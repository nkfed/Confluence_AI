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

    async def auto_tag_page(self, page_id: str, space_key: Optional[str] = None, dry_run: Optional[bool] = None) -> dict:
        """
        Auto-tag a Confluence page using AI with unified architecture.
        
        Режимна матриця:
        - TEST: завжди dry_run=True
        - SAFE_TEST: dry_run керується параметром
        - PROD: dry_run керується параметром
        
        Whitelist підтримка (якщо space_key надано):
        - Перевіряє page_id через whitelist
        - Повертає 403 якщо сторінка не в whitelist
        
        Args:
            page_id: Confluence page ID
            space_key: Optional space key for whitelist validation
            dry_run: If True, performs dry-run. Ignored in TEST mode (always dry-run)
            
        Returns:
            {
                "status": "dry_run" | "updated" | "forbidden",
                "page_id": str,
                "mode": str,
                "dry_run": bool,
                "whitelist_enabled": bool,
                "tags": {
                    "proposed": list,
                    "existing": list,
                    "added": list (or "to_add" in dry-run)
                } | null (for forbidden)
            }
        """
        from src.core.whitelist.whitelist_manager import WhitelistManager
        
        mode = self.agent.mode
        
        # ✅ Уніфікована dry_run матриця
        if mode == "TEST":
            effective_dry_run = True
            logger.info(f"[AutoTag] TEST mode - forcing dry_run=True (received dry_run={dry_run})")
        elif mode == "SAFE_TEST":
            effective_dry_run = dry_run if dry_run is not None else True
            logger.info(f"[AutoTag] SAFE_TEST mode - dry_run={effective_dry_run}")
        elif mode == "PROD":
            effective_dry_run = dry_run if dry_run is not None else True
            logger.info(f"[AutoTag] PROD mode - dry_run={effective_dry_run}")
        else:
            effective_dry_run = True
            logger.warning(f"[AutoTag] Unknown mode '{mode}' - defaulting to dry_run=True")
        
        logger.info(
            f"[AutoTag] Starting auto-tag for page_id={page_id}, "
            f"mode={mode}, dry_run_param={dry_run}, effective_dry_run={effective_dry_run}, space_key={space_key}"
        )
        
        # ✅ Whitelist validation (якщо space_key надано)
        whitelist_enabled = False
        allowed_ids = None
        if space_key:
            whitelist_enabled = True
            whitelist_manager = WhitelistManager()
            
            try:
                allowed_ids = await whitelist_manager.get_allowed_ids(space_key, self.confluence)
                logger.info(f"[AutoTag] Whitelist loaded: {len(allowed_ids)} allowed pages for {space_key}")
                logger.debug(f"[AutoTag] Allowed IDs: {sorted(list(allowed_ids))[:20]}")
                
                page_id_int = int(page_id)
                
                if page_id_int not in allowed_ids:
                    logger.warning(f"[AutoTag] Page {page_id} not in whitelist for space {space_key}")
                    return {
                        "status": "forbidden",
                        "page_id": page_id,
                        "mode": mode,
                        "dry_run": effective_dry_run,
                        "whitelist_enabled": whitelist_enabled,
                        "message": f"Page {page_id} not in whitelist for space {space_key}",
                        "tags": None
                    }
                
                logger.info(f"[AutoTag] Page {page_id} validated through whitelist")
            except Exception as e:
                logger.error(f"[AutoTag] Whitelist validation failed: {e}")
                return {
                    "status": "error",
                    "page_id": page_id,
                    "mode": mode,
                    "dry_run": effective_dry_run,
                    "whitelist_enabled": whitelist_enabled,
                    "message": f"Whitelist validation failed: {str(e)}",
                    "tags": None
                }

        logger.info(f"[AutoTag] Fetching page {page_id}")
        page = await self.confluence.get_page(page_id)

        if not page:
            logger.error(f"[AutoTag] Page {page_id} not found")
            return {
                "status": "error",
                "page_id": page_id,
                "mode": mode,
                "dry_run": effective_dry_run,
                "whitelist_enabled": whitelist_enabled,
                "message": "Page not found",
                "tags": None
            }

        text = page.get("body", {}).get("storage", {}).get("value", "")
        logger.debug(f"[AutoTag] Extracted text length: {len(text)}")

        logger.info(f"[AutoTag] Calling TaggingAgent for page {page_id}")
        tags = await self.agent.suggest_tags(text)

        logger.info(f"[AutoTag] Suggested tags: {tags}")

        # Flatten tags and fetch existing labels
        flat_tags = flatten_tags(tags)
        logger.debug(f"[AutoTag] Flattened tags: {flat_tags}")
        
        existing_labels = await self.confluence.get_labels(page_id)
        logger.debug(f"[AutoTag] Existing labels: {existing_labels}")
        
        # Calculate differences
        proposed = set(flat_tags)
        existing = set(existing_labels)
        to_add = proposed - existing
        
        logger.info(f"[AutoTag] Tag comparison: proposed={len(proposed)}, existing={len(existing)}, to_add={len(to_add)}")

        # Dry-run logic: don't update Confluence
        if effective_dry_run:
            logger.info(f"[DRY-RUN] Would add labels for {page_id}: {list(to_add)}")
            return {
                "status": "dry_run",
                "page_id": page_id,
                "mode": mode,
                "dry_run": effective_dry_run,
                "whitelist_enabled": whitelist_enabled,
                "tags": {
                    "proposed": list(proposed),
                    "existing": list(existing),
                    "added": [],
                    "to_add": list(to_add)
                }
            }

        # Check page policy before updating
        try:
            # ✅ Передаємо allowed_ids для коректної перевірки whitelist
            allowed_pages_list = list(allowed_ids) if allowed_ids else None
            logger.info(f"[AutoTag] Enforcing policy for page {page_id} with allowed_pages={allowed_pages_list}")
            self.agent.enforce_page_policy(page_id, allowed_pages=allowed_pages_list)
        except PermissionError as e:
            logger.warning(f"[AutoTag] Page {page_id} blocked by policy: {e}")
            return {
                "status": "forbidden",
                "page_id": page_id,
                "mode": mode,
                "dry_run": effective_dry_run,
                "whitelist_enabled": whitelist_enabled,
                "message": str(e),
                "tags": None
            }
        
        # Real update - only add new tags
        if to_add:
            logger.info(f"[AutoTag] Updating labels for page {page_id}: adding {list(to_add)}")
            await self.confluence.update_labels(page_id, list(to_add))
            logger.info(f"[AutoTag] Successfully updated labels for page {page_id}")
        else:
            logger.info(f"[AutoTag] No new labels to add for page {page_id}")

        return {
            "status": "updated",
            "page_id": page_id,
            "mode": mode,
            "dry_run": effective_dry_run,
            "whitelist_enabled": whitelist_enabled,
            "tags": {
                "proposed": list(proposed),
                "existing": list(existing),
                "added": list(to_add),
                "to_add": []
            }
        }
