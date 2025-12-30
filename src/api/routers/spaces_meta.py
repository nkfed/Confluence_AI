"""
API роутер для отримання метаданих просторів Confluence.

GET /spaces/meta - повертає доступні типи та статуси просторів
"""

from fastapi import APIRouter
from src.services.space_service import SpaceService
from src.core.logging.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["spaces"])


@router.get("/spaces/meta")
async def get_spaces_metadata():
    """
    Отримати метадані про простори Confluence.
    
    Повертає:
    - available_types: унікальні типи просторів (global, personal, etc.)
    - available_statuses: унікальні статуси (current, archived, etc.)
    
    Використовується для:
    - Побудови UI фільтрів
    - Валідації параметрів exclude_types та exclude_statuses
    - Розуміння структури просторів
    
    Returns:
        {
            "available_types": ["global", "personal"],
            "available_statuses": ["current", "archived"]
        }
    """
    logger.info("GET /spaces/meta called")
    
    try:
        service = SpaceService()
        result = await service.get_spaces_meta()
        
        logger.info(
            f"Successfully retrieved spaces metadata: "
            f"{len(result['available_types'])} types, "
            f"{len(result['available_statuses'])} statuses"
        )
        return result
        
    except Exception as e:
        logger.error(f"Error getting spaces metadata: {e}")
        return {
            "error": str(e),
            "available_types": [],
            "available_statuses": []
        }
