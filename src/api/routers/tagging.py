from typing import Optional
from fastapi import APIRouter, Query
from src.services.tagging_service import TaggingService

router = APIRouter(prefix="/pages", tags=["tagging"])

@router.post("/{page_id}/auto-tag")
async def auto_tag_page(
    page_id: str,
    dry_run: Optional[bool] = Query(
        default=None, 
        description="Override agent mode. If None, uses TAGGING_AGENT_MODE"
    )
):
    """
    Auto-tag a Confluence page using AI with structured tag comparison.
    
    Returns detailed tag analysis:
    - proposed: AI-generated tags
    - existing: current page tags
    - added: tags that were actually written (proposed - existing)
    
    Respects TAGGING_AGENT_MODE:
    - TEST: dry-run (no updates)
    - SAFE_TEST: whitelist only
    - PROD: all pages
    
    Args:
        page_id: Confluence page ID
        dry_run: Optional override. If None, uses agent mode
        
    Returns:
        {
            "status": "updated" | "dry_run" | "forbidden",
            "page_id": str,
            "tags": {
                "proposed": [...],
                "existing": [...],
                "added": [...]  // or "to_add" in dry-run
            } | null  // for forbidden
        }
    """
    service = TaggingService()
    return await service.auto_tag_page(page_id, dry_run=dry_run)
