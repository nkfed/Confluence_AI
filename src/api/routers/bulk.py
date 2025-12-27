from typing import List, Optional
from fastapi import APIRouter, Query
from pydantic import BaseModel
from src.services.bulk_tagging_service import BulkTaggingService

router = APIRouter(prefix="/bulk", tags=["bulk"])


class BulkTagRequest(BaseModel):
    """Request model for bulk tagging operation"""
    page_ids: List[str]
    dry_run: bool = False


@router.post("/tag-pages")
async def bulk_tag_pages(request: BulkTagRequest):
    """
    Bulk tag multiple Confluence pages using AI.
    
    Args:
        request: BulkTagRequest with page_ids and dry_run flag
        
    Returns:
        {
            "total": int,
            "processed": int,
            "success": int,
            "errors": int,
            "dry_run": bool,
            "details": [
                {
                    "page_id": str,
                    "status": "updated" | "dry_run" | "error",
                    "tags": {
                        "proposed": list,
                        "existing": list,
                        "added": list,
                        "to_add": list  (only in dry_run)
                    }
                }
            ]
        }
    """
    service = BulkTaggingService()
    result = await service.tag_pages(request.page_ids, dry_run=request.dry_run)
    return result


@router.post("/tag-space/{space_key}")
async def bulk_tag_space(
    space_key: str,
    dry_run: Optional[bool] = Query(
        default=None,
        description="Override agent mode. If None, uses TAGGING_AGENT_MODE"
    )
):
    """
    Bulk tag all pages in a Confluence space using AI.
    
    Respects TAGGING_AGENT_MODE:
    - TEST: dry-run (no updates)
    - SAFE_TEST: whitelist only
    - PROD: all pages
    
    Args:
        space_key: Confluence space key
        dry_run: Optional override. If None, uses agent mode
        
    Returns:
        {
            "total": int,
            "processed": int,
            "success": int,
            "errors": int,
            "dry_run": bool,
            "details": [
                {
                    "page_id": str,
                    "status": "updated" | "dry_run" | "forbidden" | "error",
                    "tags": {...} | null
                }
            ]
        }
    """
    service = BulkTaggingService()
    result = await service.tag_space(space_key, dry_run=dry_run)
    return result


@router.get("/")
def bulk_root():
    return {"message": "Bulk operations API - use /bulk/tag-pages for bulk tagging"}
