"""
API роутер для отримання списку просторів Confluence.

GET /spaces - з підтримкою фільтрації за типами та статусами
"""

from typing import Optional, List
from fastapi import APIRouter, Query, Depends
from src.services.space_service import SpaceService
from src.core.logging.logger import get_logger
from src.models.space_models import SpaceFilterParams

logger = get_logger(__name__)

router = APIRouter(tags=["spaces"])


def normalize_list_param(values: List[str]) -> List[str]:
    """
    Нормалізує параметри списку, видаляючи лапки, дужки та зайві пробіли.
    Також розділяє значення за комами.
    
    Приклади:
    - ['personal'] -> ['personal']
    - ["global"] -> ['global']
    - "personal, global" -> ['personal', 'global']
    - "personal,global,team" -> ['personal', 'global', 'team']
    
    Args:
        values: Список значень з можливими лапками/дужками/комами
        
    Returns:
        Нормалізований список значень
    """
    normalized = []
    for v in values:
        # Видалити дужки, лапки та пробіли
        v = v.strip("[]'\" ")
        
        # Якщо значення містить кому - розділити на окремі елементи
        if ',' in v:
            parts = [part.strip("[]'\" ") for part in v.split(',')]
            normalized.extend([p for p in parts if p])
        elif v:
            normalized.append(v)
    
    return normalized


@router.get("/spaces")
async def get_spaces(
    query: Optional[str] = Query(None, description="Search query for spaces (spaceKey or name)"),
    accessible_only: bool = Query(True, description="Return only accessible spaces"),
    start: int = Query(0, ge=0, description="Start index for pagination"),
    limit: int = Query(25, ge=1, le=100, description="Maximum number of results (1-100)"),
    exclude_types: List[str] = Query([], description="Space types to exclude. Add each value separately. Example: personal, global"),
    exclude_statuses: List[str] = Query([], description="Space statuses to exclude. Add each value separately. Example: archived"),
    name_contains: Optional[str] = Query(None, description="Substring to match in space name (case-insensitive). Example: ЕСОЗ")
):
    """
    Отримати список просторів Confluence з фільтрацією.
    
    Фільтрація (OR логіка):
    - Виключає простір якщо type ∈ exclude_types АБО status ∈ exclude_statuses
    
    Приклади:
    - Виключити архівовані: ?exclude_statuses=archived
    - Виключити personal простори: ?exclude_types=personal
    - Виключити архівовані та personal: ?exclude_types=personal&exclude_types=global&exclude_statuses=archived
    
    ВАЖЛИВО: При фільтрації автоматично завантажуються додаткові сторінки
    щоб набрати потрібну кількість відфільтрованих просторів.
        
    Returns:
        {
            "spaces": [
                {
                    "id": str,
                    "key": str,
                    "name": str,
                    "type": str,
                    "status": str
                }
            ],
            "start": int,
            "limit": int,
            "size": int,
            "total": int
        }
    """
    logger.info(
        f"GET /spaces: query={query}, start={start}, limit={limit}, "
        f"exclude_types={exclude_types}, exclude_statuses={exclude_statuses}, name_contains={name_contains}"
    )
    
    # Нормалізувати параметри (видалити лапки, дужки, розділити за комами)
    exclude_types = normalize_list_param(exclude_types) if exclude_types else []
    exclude_statuses = normalize_list_param(exclude_statuses) if exclude_statuses else []
    
    if exclude_types or exclude_statuses or name_contains:
        logger.info(f"Normalized filters: exclude_types={exclude_types}, exclude_statuses={exclude_statuses}, name_contains={name_contains}")
    
    try:
        service = SpaceService()
        result = await service.get_spaces(
            query=query,
            accessible_only=accessible_only,
            start=start,
            limit=limit,
            exclude_types=exclude_types if exclude_types else None,
            exclude_statuses=exclude_statuses if exclude_statuses else None,
            name_contains=name_contains
        )
        
        logger.info(f"Successfully retrieved {result.get('size')} spaces")
        return result
        
    except Exception as e:
        logger.error(f"Error getting spaces: {e}")
        return {
            "error": str(e),
            "spaces": [],
            "start": start,
            "limit": limit,
            "size": 0,
            "total": 0
        }
