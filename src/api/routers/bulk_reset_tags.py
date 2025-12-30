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
    ),
    root_id: Optional[str] = Query(
        default=None,
        description="Optional root page ID - if provided, only process descendants of this page"
    )
):
    """
    Скинути теги на всіх сторінках простору або в межах дерева сторінок.
    
    Функціональність:
    - Якщо root_id надано → отримує лише нащадків цієї сторінки
    - Якщо root_id немає → обробляє весь простір
    - Визначає теги для видалення (за категоріями або всі AI-теги)
    - Якщо dry_run=false → видаляє теги
    
    Args:
        space_key: Ключ простору Confluence
        categories: Категорії тегів для видалення (comma-separated: doc,domain,kb,tool)
        dry_run: Dry-run режим (за замовчуванням true)
        root_id: Опціональний ID кореневої сторінки для обробки лише дерева
        
    Returns:
        {
            "total": int,
            "processed": int,
            "removed": int,
            "no_tags": int,
            "errors": int,
            "dry_run": bool,
            "scope": "space" | "tree",
            "root_id": str | None,
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
    logger.info(f"POST /bulk/reset-tags/{space_key}: categories={categories}, dry_run={dry_run}, root_id={root_id}")
    
    try:
        # Парсинг категорій
        category_list = None
        if categories:
            category_list = [c.strip() for c in categories.split(",") if c.strip()]
            logger.info(f"Parsed categories: {category_list}")
        
        reset_service = TagResetService()
        
        # Визначення scope та отримання сторінок
        if root_id:
            # Tree scope - validate and fetch tree
            scope = "tree"
            logger.info(f"Tree scope: validating root_id={root_id} for space={space_key}")
            
            # Validate that root_id belongs to space_key
            try:
                root_page = await reset_service.confluence.get_page(root_id, expand="space")
                page_space_key = root_page.get("space", {}).get("key")
                
                if page_space_key != space_key:
                    logger.error(
                        f"root_id={root_id} belongs to space '{page_space_key}', "
                        f"not '{space_key}'"
                    )
                    return {
                        "total": 0,
                        "processed": 0,
                        "removed": 0,
                        "no_tags": 0,
                        "errors": 1,
                        "dry_run": dry_run,
                        "scope": "tree",
                        "root_id": root_id,
                        "error": f"root_id {root_id} does not belong to space {space_key}",
                        "details": []
                    }
                
                logger.info(f"Root page validation successful for {root_id}")
                
            except Exception as e:
                logger.error(f"Failed to validate root_id={root_id}: {e}")
                return {
                    "total": 0,
                    "processed": 0,
                    "removed": 0,
                    "no_tags": 0,
                    "errors": 1,
                    "dry_run": dry_run,
                    "scope": "tree",
                    "root_id": root_id,
                    "error": f"Invalid root_id: {str(e)}",
                    "details": []
                }
            
            # Fetch tree pages
            page_ids = await reset_service.collect_tree_pages(root_id)
            logger.info(f"Fetched {len(page_ids)} pages from tree starting at {root_id}")
            
            # Скинути теги в дереві
            result = await reset_service.reset_tree_tags(
                page_ids=page_ids,
                categories=category_list,
                dry_run=dry_run
            )
        else:
            # Space scope - fetch all pages
            scope = "space"
            logger.info(f"Space scope: fetching all pages from {space_key}")
            
            space_service = SpaceService()
            pages = await space_service.get_space_pages(space_key, expand="")  # Не потрібен body
            logger.info(f"Fetched {len(pages)} pages from space {space_key}")
            
            # Скинути теги
            result = await reset_service.reset_space_tags(
                pages=pages,
                categories=category_list,
                dry_run=dry_run
            )
        
        # Add scope and root_id to result
        result["scope"] = scope
        result["root_id"] = root_id
        
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
            "scope": "tree" if root_id else "space",
            "root_id": root_id,
            "error": str(e),
            "details": []
        }
