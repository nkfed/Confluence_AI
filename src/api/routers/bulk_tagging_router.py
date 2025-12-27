from fastapi import APIRouter, Body
from typing import List
from src.services.bulk_tagging_service import BulkTaggingService
from src.clients.confluence_client import ConfluenceClient
from src.core.logging.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/bulk", tags=["bulk"])


@router.post("/tag-pages", summary="Tag multiple pages by IDs")
async def tag_pages(
    page_ids: List[str] = Body(
        ..., 
        description="List of Confluence page IDs to tag",
        embed=True
    ),
    dry_run: bool = Body(
        True, 
        description="If True, performs a dry run without actually applying tags",
        embed=True
    )
):
    """
    Tags multiple Confluence pages by their IDs.
    
    - **page_ids**: List of page IDs to process
    - **dry_run**: When True, simulates tagging without applying changes
    
    Returns statistics about successful, skipped, and failed tagging operations.
    """
    logger.info(f"POST /bulk/tag-pages called with {len(page_ids)} page_ids, dry_run={dry_run}")
    
    confluence_client = ConfluenceClient()
    service = BulkTaggingService(confluence_client=confluence_client)
    
    return await service.tag_pages(page_ids, dry_run=dry_run)


@router.post("/tag-tree/{root_page_id}", summary="Tag page tree starting from root")
async def tag_tree(
    root_page_id: str,
    dry_run: bool = Body(
        True, 
        description="If True, performs a dry run without actually applying tags",
        embed=True
    )
):
    """
    Tags a page and all its descendants in the page tree.
    
    - **root_page_id**: The ID of the root page
    - **dry_run**: When True, simulates tagging without applying changes
    
    Recursively collects all child pages and applies tagging to the entire tree.
    
    **Unified Response Structure (per page):**
    - `page_id`: Confluence page ID
    - `title`: Page title
    - `status`: "updated", "dry_run", "no_changes", or "error"
    - `skipped`: Boolean indicating if page was skipped
    - `tags`: Unified tag structure:
      - `proposed`: AI-generated tags
      - `existing`: Current page labels
      - `to_add`: Tags to be added (populated in dry-run mode)
      - `added`: Tags actually added (populated in real update mode)
    - `dry_run`: Boolean indicating if this was a dry run
    
    Returns statistics about successful, skipped, and failed tagging operations.
    """
    logger.info(f"POST /bulk/tag-tree/{root_page_id} called with dry_run={dry_run}")
    
    confluence_client = ConfluenceClient()
    service = BulkTaggingService(confluence_client=confluence_client)
    
    return await service.tag_tree(root_page_id, dry_run=dry_run)


@router.post("/tag-space/{space_key}", summary="Tag all pages in a Confluence space")
async def tag_space(
    space_key: str,
    dry_run: bool = Body(
        True, 
        description="If True, performs a dry run without actually applying tags",
        embed=True
    )
):
    """
    Tags all pages in a specified Confluence space.
    
    - **space_key**: The key of the Confluence space (e.g., 'PROJ', 'TEAM')
    - **dry_run**: When True, simulates tagging without applying changes
    
    Fetches all pages in the space and applies tagging to each one.
    Returns statistics about successful, skipped, and failed tagging operations.
    """
    logger.info(f"POST /bulk/tag-space/{space_key} called with dry_run={dry_run}")
    
    confluence_client = ConfluenceClient()
    service = BulkTaggingService(confluence_client=confluence_client)
    
    return await service.tag_space(space_key, dry_run=dry_run)
