from typing import List, Optional
from fastapi import APIRouter, Query
from src.services.bulk_tagging_service import BulkTaggingService
from src.models.tag_pages_models import TagPagesRequest

router = APIRouter(prefix="/bulk", tags=["bulk"])


@router.post("/tag-pages")
async def bulk_tag_pages(request: TagPagesRequest):
    """
    Bulk tag multiple Confluence pages using AI with whitelist control.
    
    Args:
        request: TagPagesRequest with space_key, page_ids and dry_run flag
        
    Returns:
        {
            "total": int,
            "processed": int,
            "success": int,
            "errors": int,
            "skipped_by_whitelist": int,
            "mode": str,
            "dry_run": bool,
            "whitelist_enabled": bool,
            "details": [
                {
                    "page_id": str,
                    "status": "updated" | "dry_run" | "error",
                    "tags": {
                        "proposed": list,
                        "existing": list,
                        "added": list,
                        "to_add": list
                    },
                    "dry_run": bool
                }
            ]
        }
    """
    service = BulkTaggingService()
    result = await service.tag_pages(
        page_ids=request.page_ids,
        space_key=request.space_key,
        dry_run=request.dry_run
    )
    return result


# @router.post("/tag-space/{space_key}")
# REMOVED: Duplicate endpoint - use bulk_tag_space.py router instead
# This endpoint has been removed to avoid conflict with the extended version
# in src/api/routers/bulk_tag_space.py which provides additional filtering options


@router.post("/tag-tree/{space_key}/{root_page_id}")
async def bulk_tag_tree(
    space_key: str,
    root_page_id: str,
    dry_run: Optional[bool] = Query(
        default=None,
        description="Override agent mode. If None, uses TAGGING_AGENT_MODE"
    )
):
    """
    Tag a page and all its descendants in the page tree with whitelist control.
    
    Args:
        space_key: Confluence space key (used for whitelist lookup)
        root_page_id: The ID of the root page
        dry_run: Optional override. If None, uses agent mode
        
    Returns:
        Dictionary with tagging results including tree traversal info
    """
    service = BulkTaggingService()
    result = await service.tag_tree(
        root_page_id=root_page_id,
        space_key=space_key,
        dry_run=dry_run
    )
    return result


@router.get("/")
def bulk_root():
    return {"message": "Bulk operations API - use /bulk/tag-pages for bulk tagging"}
