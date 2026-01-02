from typing import Optional
from fastapi import APIRouter, Query
from src.services.tagging_service import TaggingService

router = APIRouter(prefix="/pages", tags=["tagging"])

@router.post("/{page_id}/auto-tag")
async def auto_tag_page(
    page_id: str,
    space_key: Optional[str] = Query(
        default=None,
        description="Space key for whitelist validation (optional)"
    ),
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
    - TEST: always dry-run (no updates)
    - SAFE_TEST: dry_run parameter controls behavior
    - PROD: dry_run parameter controls behavior
    
    Whitelist support (when space_key provided):
    - Validates page_id against whitelist
    - Returns 403 if page not in whitelist
    
    Args:
        page_id: Confluence page ID
        space_key: Optional space key for whitelist validation
        dry_run: Optional override. If None, uses agent mode
        
    Returns:
        {
            "status": "updated" | "dry_run" | "forbidden",
            "page_id": str,
            "mode": str,
            "dry_run": bool,
            "whitelist_enabled": bool,
            "tags": {
                "proposed": [...],
                "existing": [...],
                "added": [...]  // or "to_add" in dry-run
            } | null  // for forbidden
        }
    """
    service = TaggingService()
    result = await service.auto_tag_page(page_id, space_key=space_key, dry_run=dry_run)

    # Add root_page_id to the response
    result["root_page_id"] = page_id

    return result
