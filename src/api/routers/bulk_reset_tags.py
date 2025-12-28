"""
API роутер для скидання тегів у просторі Confluence.

POST /bulk/reset-tags/{space_key}
"""

from typing import Optional, List
from fastapi import APIRouter, Path, Query
from pydantic import BaseModel
from src.services.space_service import SpaceService
from src.services.tag_reset_service import TagResetService
from src.core.logging.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/bulk", tags=["bulk"])


class ResetTagsRequest(BaseModel):
    """Request model для скидання тегів"""
    categories: Optional[List[str]] = None  # None = всі AI-теги
    dry_run: bool = True


@router.post("/reset-tags/{space_key}")
async def reset_tags_in_space(
    space_key: str = Path(..., description="Confluence space key"),
    categories: Optional[str] = Query(
        default=None,
        description="Comma-separated list of categories (doc,domain,kb,tool). None = all AI tags"
    ),
    dry_run: bool = Query(
        default=True,
        description="Dry run mode (no actual changes)"
    )
):
    """
    Скинути теги на всіх сторінках простору.
    
    Функціональність:
    - Отримує всі сторінки простору
    - Визначає теги для видалення (за категоріями або всі AI-теги)
    - Якщо dry_run=false → видаляє теги
    
    Args:
        space_key: Ключ простору Confluence
        categories: Категорії тегів для видалення (comma-separated: doc,domain,kb,tool)
        dry_run: Dry-run режим (за замовчуванням true)
        
    Returns:
        {
            "total": int,
            "processed": int,
            "removed": int,
            "no_tags": int,
            "errors": int,
            "dry_run": bool,
            "details": [
                {
                    "page_id": str,
                    "title": str,
                    "status": "removed" | "dry_run" | "no_tags" | "error",
                    "removed_tags": List[str],
                    "skipped": bool
                }
            ]
        }
    """
    logger.info(f"POST /bulk/reset-tags/{space_key}: categories={categories}, dry_run={dry_run}")
    
    try:
        # Парсинг категорій
        category_list = None
        if categories:
            category_list = [c.strip() for c in categories.split(",") if c.strip()]
            logger.info(f"Parsed categories: {category_list}")
        
        # Отримати всі сторінки простору
        space_service = SpaceService()
        pages = await space_service.get_space_pages(space_key, expand="")  # Не потрібен body
        
        logger.info(f"Fetched {len(pages)} pages from space {space_key}")
        
        # Скинути теги
        reset_service = TagResetService()
        result = await reset_service.reset_space_tags(
            pages=pages,
            categories=category_list,
            dry_run=dry_run
        )
        
        logger.info(f"Reset complete: {result.get('removed')} pages processed")
        return result
        
    except Exception as e:
        logger.error(f"Error resetting tags in space {space_key}: {e}")
        return {
            "total": 0,
            "processed": 0,
            "removed": 0,
            "no_tags": 0,
            "errors": 1,
            "dry_run": dry_run,
            "error": str(e),
            "details": []
        }
