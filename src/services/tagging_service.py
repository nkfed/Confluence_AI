from typing import Optional
from src.agents.tagging_agent import TaggingAgent
from src.clients.confluence_client import ConfluenceClient
from src.core.logging.logger import get_logger

logger = get_logger(__name__)


def flatten_tags(tag_dict: dict[str, list[str]]) -> list[str]:
    """
    Flatten tag dictionary to a flat list of tags.
    
    Args:
        tag_dict: Dictionary like {"doc": ["doc-tech"], "domain": ["domain-helpdesk-site"]}
        
    Returns:
        Flat list like ["doc-tech", "domain-helpdesk-site"]
    """
    return [tag for tags in tag_dict.values() for tag in tags]


class TaggingService:
    def __init__(self, confluence_client: ConfluenceClient = None, tagging_agent: TaggingAgent = None):
        self.confluence = confluence_client or ConfluenceClient()
        self.agent = tagging_agent or TaggingAgent()

    async def auto_tag_page(self, page_id: str, dry_run: Optional[bool] = None) -> dict:
        """
        Auto-tag a Confluence page using AI with structured tag comparison.
        
        Returns tag comparison similar to bulk/tag-pages:
        - proposed: AI-generated tags
        - existing: current page tags
        - added: tags that were actually written (proposed - existing)
        
        Respects TAGGING_AGENT_MODE:
        - TEST: dry-run (no updates)
        - SAFE_TEST: whitelist only
        - PROD: all pages
        
        Args:
            page_id: Confluence page ID
            dry_run: Optional override. If None, uses agent.is_dry_run()
            
        Returns:
            {
                "status": "dry_run" | "updated" | "forbidden",
                "page_id": str,
                "tags": {
                    "proposed": list,
                    "existing": list,
                    "added": list (or "to_add" in dry-run)
                } | null (for forbidden)
            }
        """
        # Use agent mode if dry_run not explicitly provided
        if dry_run is None:
            dry_run = self.agent.is_dry_run()
            logger.info(f"[TaggingService] Using agent mode: {self.agent.mode}, dry_run={dry_run}")
        else:
            logger.info(f"[TaggingService] Using explicit dry_run={dry_run}")

        logger.info(f"[TaggingService] Fetching page {page_id}")
        page = await self.confluence.get_page(page_id)

        if not page:
            logger.error(f"[TaggingService] Page {page_id} not found")
            return {"status": "error", "page_id": page_id, "message": "Page not found", "tags": None}

        text = page.get("body", {}).get("storage", {}).get("value", "")
        logger.debug(f"[TaggingService] Extracted text length: {len(text)}")

        logger.info(f"[TaggingService] Calling TaggingAgent for page {page_id}")
        tags = await self.agent.suggest_tags(text)

        logger.info(f"[TaggingService] Suggested tags: {tags}")

        # Flatten tags and fetch existing labels
        flat_tags = flatten_tags(tags)
        logger.debug(f"[TaggingService] Flattened tags: {flat_tags}")
        
        existing_labels = await self.confluence.get_labels(page_id)
        logger.debug(f"[TaggingService] Existing labels: {existing_labels}")
        
        # Calculate differences
        proposed = set(flat_tags)
        existing = set(existing_labels)
        to_add = proposed - existing
        
        logger.info(f"[TaggingService] Tag comparison: proposed={len(proposed)}, existing={len(existing)}, to_add={len(to_add)}")

        # Dry-run logic: don't update Confluence
        if dry_run:
            logger.info(f"[DRY-RUN] Would add labels for {page_id}: {list(to_add)}")
            return {
                "status": "dry_run",
                "page_id": page_id,
                "tags": {
                    "proposed": list(proposed),
                    "existing": list(existing),
                    "added": [],
                    "to_add": list(to_add)
                }
            }

        # Check page policy before updating
        try:
            self.agent.enforce_page_policy(page_id)
        except PermissionError as e:
            logger.warning(f"[TaggingService] Page {page_id} blocked by policy: {e}")
            return {
                "status": "forbidden",
                "page_id": page_id,
                "message": str(e),
                "tags": None
            }
        
        # Real update - only add new tags
        if to_add:
            logger.info(f"[TaggingService] Updating labels for page {page_id}: adding {list(to_add)}")
            await self.confluence.update_labels(page_id, list(to_add))
            logger.info(f"[TaggingService] Successfully updated labels for page {page_id}")
        else:
            logger.info(f"[TaggingService] No new labels to add for page {page_id}")

        return {
            "status": "updated",
            "page_id": page_id,
            "tags": {
                "proposed": list(proposed),
                "existing": list(existing),
                "added": list(to_add),
                "to_add": []
            }
        }
