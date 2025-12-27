import asyncio
import time
from src.services.tagging_service import TaggingService, flatten_tags
from src.clients.confluence_client import ConfluenceClient
from src.core.logging.logger import get_logger
from settings import settings

logger = get_logger(__name__)

class BulkTaggingService:
    def __init__(self, confluence_client: ConfluenceClient = None, tagging_service: TaggingService = None):
        self.confluence = confluence_client or ConfluenceClient()
        self.tagging_service = tagging_service or TaggingService(confluence_client=self.confluence)
        
        # Create agent instance for mode/policy checking
        from src.agents.tagging_agent import TaggingAgent
        self.agent = TaggingAgent()

    async def tag_pages(self, page_ids: list[str], dry_run: bool = None) -> dict:
        """
        Bulk tag multiple pages with режимна матриця enforcement.
        
        Режимна матриця:
        - TEST: завжди dry-run, якщо dry_run=false → forbidden
        - SAFE_TEST: whitelist → updated, non-whitelist → forbidden
        - PROD: всі сторінки → updated (якщо dry_run not True)
        
        Args:
            page_ids: List of Confluence page IDs
            dry_run: Optional override. If None, uses agent.is_dry_run()
        """
        # Determine final dry_run value
        if dry_run is None:
            dry_run = self.agent.is_dry_run()
            logger.info(f"[Bulk] Using agent mode: {self.agent.mode}, dry_run={dry_run}")
        else:
            logger.info(f"[Bulk] Using explicit dry_run={dry_run}")
        
        results = []
        success_count = 0
        skipped_due_to_whitelist = 0
        error_count = 0

        logger.info(
            f"[Bulk] Starting tagging for {len(page_ids)} pages "
            f"(mode={self.agent.mode}, dry_run={dry_run})"
        )

        # Process all pages - policy checks will be done per-page
        logger.info(f"[Bulk] Processing all {len(page_ids)} pages (mode={self.agent.mode})")

        # Process all pages
        for page_id in page_ids:
            try:
                logger.info(f"[Bulk] Processing page {page_id} (dry_run={dry_run})")
                
                # Завантажуємо контент сторінки
                page = await self.confluence.get_page(page_id)
                if not page:
                    logger.warning(f"[Bulk] Page {page_id} not found")
                    error_count += 1
                    results.append({
                        "page_id": page_id,
                        "status": "error",
                        "message": "Page not found"
                    })
                    continue
                
                text = page.get("body", {}).get("storage", {}).get("value", "")
                logger.debug(f"[Bulk] Extracted {len(text)} chars from page {page_id}")
                
                # Формуємо індивідуальний AI-промпт на основі контенту
                from src.agents.tagging_agent import TaggingAgent
                agent = TaggingAgent()
                tags = await agent.suggest_tags(text)
                
                logger.info(f"[Bulk] Generated tags for {page_id}: {tags}")
                
                # Flatten tags and compare with existing
                flat_tags = flatten_tags(tags)
                logger.debug(f"[Bulk] Flattened tags: {flat_tags}")
                
                # Get existing labels
                existing_labels = await self.confluence.get_labels(page_id)
                logger.debug(f"[Bulk] Existing labels: {existing_labels}")
                
                # Calculate differences
                proposed = set(flat_tags)
                existing = set(existing_labels)
                to_add = proposed - existing
                
                logger.info(f"[Bulk] Tag comparison for {page_id}: proposed={len(proposed)}, existing={len(existing)}, to_add={len(to_add)}")
                
                # Dry-run mode: NO updates, just return proposed tags
                if dry_run:
                    logger.info(f"[Bulk] [DRY-RUN] Would add labels for {page_id}: {list(to_add)}")
                    success_count += 1
                    results.append({
                        "page_id": page_id,
                        "status": "dry_run",
                        "tags": {
                            "proposed": list(proposed),
                            "existing": list(existing),
                            "added": [],
                            "to_add": list(to_add)
                        }
                    })
                    continue
                
                # Real update mode: check policy FIRST
                try:
                    self.agent.enforce_page_policy(page_id)
                except PermissionError as e:
                    logger.warning(f"[Bulk] Page {page_id} blocked by policy: {e}")
                    results.append({
                        "page_id": page_id,
                        "status": "forbidden",
                        "message": str(e),
                        "tags": None
                    })
                    continue
                
                # Policy check passed - update labels
                if to_add:
                    logger.info(f"[Bulk] Updating labels for page {page_id}: adding {list(to_add)}")
                    await self.confluence.update_labels(page_id, list(to_add))
                    logger.info(f"[Bulk] Successfully updated labels for page {page_id}")
                else:
                    logger.info(f"[Bulk] No new labels to add for page {page_id}")
                
                success_count += 1
                results.append({
                    "page_id": page_id,
                    "status": "updated",
                    "tags": {
                        "proposed": list(proposed),
                        "existing": list(existing),
                        "added": list(to_add),
                        "to_add": []
                    }
                })

            except Exception as e:
                logger.error(f"[Bulk] Failed to process page {page_id}: {e}")
                error_count += 1
                results.append({
                    "page_id": page_id,
                    "status": "error",
                    "message": str(e),
                    "tags": None
                })

            # Throttling
            await asyncio.sleep(0.3)

        # Final result
        logger.info(f"[Bulk] Tagging completed: {success_count} success, {error_count} errors")
        
        return {
            "total": len(page_ids),
            "processed": len(page_ids),
            "success": success_count,
            "errors": error_count,
            "dry_run": dry_run,
            "details": results
        }

    async def tag_tree(self, root_page_id: str, dry_run: bool = False) -> dict:
        """
        Tags entire documentation tree with dynamic whitelist based on section.
        
        New architecture:
        1. Detect section by root_page_id
        2. Get allowed_labels for that section
        3. Collect all page_ids in tree (becomes temporary whitelist)
        4. For each page: generate tags using allowed_labels, filter, and update
        
        Args:
            root_page_id: Root page ID of the documentation tree
            dry_run: If True, only simulate tagging without updating Confluence
            
        Returns:
            Dictionary with tagging results
        """
        from src.sections.section_detector import detect_section, detect_section_safe
        from src.sections.whitelist import get_allowed_labels, get_default_labels
        from src.agents.summary_agent import SummaryAgent
        from src.utils.html_to_text import html_to_text
        
        logger.info(f"[tag-tree] Starting tag-tree operation for root_page_id={root_page_id} (dry_run={dry_run})")
        
        # ✅ Step 0: Enforce root page policy (PROD allows all, TEST/SAFE_TEST needs whitelist)
        try:
            self.agent.enforce_root_policy(root_page_id)
        except PermissionError as e:
            logger.error(f"[tag-tree] Root page policy violation: {e}")
            return {
                "status": "error",
                "message": str(e),
                "total": 0,
                "processed": 0,
                "success": 0,
                "errors": 1
            }
        
        # Step 1: Detect section (in PROD mode, use safe detection with fallback)
        if self.agent.mode == "PROD":
            section = detect_section_safe(root_page_id, default="unknown")
            logger.info(f"[tag-tree] Detected section: {section} (PROD mode, using safe detection)")
        else:
            try:
                section = detect_section(root_page_id)
                logger.info(f"[tag-tree] Detected section: {section}")
            except ValueError as e:
                logger.error(f"[tag-tree] Failed to detect section: {e}")
                return {
                    "status": "error",
                    "message": str(e),
                    "total": 0,
                    "processed": 0,
                    "success": 0,
                    "errors": 1
                }
        
        # Step 2: Get allowed labels for this section
        if section == "unknown":
            # PROD mode with unknown section - use default comprehensive label set
            allowed_labels = get_default_labels()
            logger.info(f"[tag-tree] Using default labels for unknown section (count={len(allowed_labels)})")
        else:
            allowed_labels = get_allowed_labels(section)
            logger.info(f"[tag-tree] Allowed labels for section '{section}': {allowed_labels} (count={len(allowed_labels)})")
        
        # Step 3: Collect all pages in tree
        logger.info(f"[tag-tree] Collecting page tree from root {root_page_id}")
        all_page_ids = await self._collect_all_children(root_page_id)
        logger.info(f"[tag-tree] Collected {len(all_page_ids)} pages in tree (TEMP_ALLOWED_PAGES)")
        
        # Step 4: Process each page
        results = []
        success_count = 0
        error_count = 0
        skipped_count = 0
        
        summary_agent = SummaryAgent()
        
        for i, page_id in enumerate(all_page_ids, 1):
            logger.info(f"[tag-tree] Processing page {i}/{len(all_page_ids)}: {page_id}")
            
            try:
                # Fetch page
                page = await self.confluence.get_page(page_id)
                if not page:
                    logger.warning(f"[tag-tree] Page {page_id} not found")
                    error_count += 1
                    results.append({
                        "page_id": page_id,
                        "status": "error",
                        "message": "Page not found"
                    })
                    continue
                
                page_title = page.get("title", "Unknown")
                logger.info(f"[tag-tree] Page title: {page_title}")
                
                # Extract content
                html_content = page.get("body", {}).get("storage", {}).get("value", "")
                text_content = html_to_text(html_content)
                logger.debug(f"[tag-tree] Extracted {len(text_content)} chars of text")
                
                # Generate tags with dynamic whitelist filtering (already deduplicated in agent)
                # Fallback to section tags if content is too short or contains only links
                logger.info(f"[tag-tree] Generating tags with allowed_labels filter")
                suggested_tags = await summary_agent.generate_tags_for_tree(
                    content=text_content,
                    allowed_labels=allowed_labels,
                    dry_run=dry_run,
                    page_id=page_id
                )
                # suggested_tags are already deduplicated and filtered by generate_tags_for_tree
                logger.info(f"[tag-tree] Generated {len(suggested_tags)} filtered tags: {suggested_tags}")
                
                # Get current labels
                current_labels = await self.confluence.get_labels(page_id)
                logger.info(f"[tag-tree] Current labels: {current_labels}")
                
                # Calculate diff
                labels_to_add = [tag for tag in suggested_tags if tag not in current_labels]
                labels_to_remove = []  # We don't remove labels in tag-tree operation
                
                logger.info(f"[tag-tree] Labels to add: {labels_to_add}")
                
                # Check if there are any changes
                has_changes = bool(labels_to_add or labels_to_remove)
                
                # Determine added field based on dry_run
                # In dry-run: added=[], in real update: added=labels_to_add
                added = []
                
                # Update labels (if not dry_run and there are changes)
                if not dry_run and has_changes:
                    logger.info(f"[tag-tree] Updating labels for page {page_id}")
                    await self.confluence.update_labels(
                        page_id=page_id,
                        labels_to_add=labels_to_add,
                        labels_to_remove=labels_to_remove
                    )
                    logger.info(f"[tag-tree] Successfully updated labels for page {page_id}")
                    status = "updated"
                    skipped = False
                    added = labels_to_add  # ✅ Tags that were actually added
                elif dry_run and has_changes:
                    logger.info(f"[tag-tree] [DRY-RUN] Would update labels for {page_id}")
                    status = "dry_run"
                    skipped = False
                    # added stays [] for dry-run
                else:
                    logger.info(f"[tag-tree] No label changes needed for page {page_id} - SKIPPED")
                    status = "no_changes"
                    skipped = True
                    skipped_count += 1
                    # added stays [] for no changes
                
                success_count += 1
                
                # ✅ Unified tags structure
                from src.utils.tag_structure import create_unified_tags_structure
                
                results.append({
                    "page_id": page_id,
                    "title": page_title,
                    "status": status,
                    "skipped": skipped,
                    "tags": create_unified_tags_structure(
                        proposed=suggested_tags,
                        existing=current_labels,
                        dry_run=dry_run
                    ),
                    "dry_run": dry_run
                })
                
            except Exception as e:
                logger.error(f"[tag-tree] Failed to process page {page_id}: {e}", exc_info=True)
                error_count += 1
                results.append({
                    "page_id": page_id,
                    "status": "error",
                    "skipped": False,
                    "message": str(e)
                })
            
            # Throttling
            await asyncio.sleep(0.3)
        
        # Log metrics
        from src.core.logging.logger import get_logger
        metrics_logger = get_logger("metrics")
        metrics_logger.info(
            f"tag_tree_operation root_page_id={root_page_id} "
            f"section={section} total_pages={len(all_page_ids)} "
            f"success={success_count} errors={error_count} "
            f"skipped={skipped_count} dry_run={dry_run}"
        )
        
        logger.info(
            f"[tag-tree] Completed: {success_count} success, {error_count} errors, "
            f"{skipped_count} skipped"
        )
        
        # Build skipped pages list
        skipped_pages = [
            {
                "page_id": r["page_id"],
                "title": r.get("title", "Unknown"),
                "reason": "no label changes"
            }
            for r in results if r.get("skipped", False)
        ]
        
        return {
            "status": "completed",
            "section": section,
            "allowed_labels": allowed_labels,
            "root_page_id": root_page_id,
            "total": len(all_page_ids),
            "processed": len(all_page_ids),
            "success": success_count,
            "errors": error_count,
            "skipped_count": skipped_count,
            "dry_run": dry_run,
            "details": results,
            "skipped_pages": skipped_pages
        }

    async def _collect_all_children(self, parent_id: str) -> list[str]:
        """Рекурсивно збирає всі ID сторінок дерева."""
        to_process = [parent_id]
        collected = []
        
        while to_process:
            current_id = to_process.pop(0)
            collected.append(current_id)
            
            children = await self.confluence.get_child_pages(current_id)
            to_process.extend(children)
            
        return collected

    async def tag_space(self, space_key: str, dry_run: Optional[bool] = None) -> dict:
        """
        Tag all pages in a Confluence space using AI.
        
        Respects TAGGING_AGENT_MODE:
        - TEST: dry-run (no updates)
        - SAFE_TEST: whitelist only
        - PROD: all pages
        
        Args:
            space_key: Confluence space key
            dry_run: Optional override. If None, uses agent.is_dry_run()
            
        Returns:
            {
                "total": int,
                "processed": int,
                "success": int,
                "errors": int,
                "dry_run": bool,
                "details": [...]
            }
        """
        # Use agent mode if dry_run not explicitly set
        if dry_run is None:
            dry_run = self.agent.is_dry_run()
            logger.info(f"[Bulk] Using agent mode: {self.agent.mode}, dry_run={dry_run}")
        else:
            logger.info(f"[Bulk] Using explicit dry_run={dry_run}")
        
        logger.info(f"[Bulk] Fetching all pages in space '{space_key}'")
        
        try:
            page_ids = await self.confluence.get_all_pages_in_space(space_key)
        except Exception as e:
            logger.error(f"[Bulk] Failed to fetch pages from space '{space_key}': {e}")
            return {
                "total": 0,
                "processed": 0,
                "success": 0,
                "errors": 1,
                "dry_run": dry_run,
                "details": [{
                    "space_key": space_key,
                    "status": "error",
                    "message": f"Failed to fetch pages: {str(e)}",
                    "tags": None
                }]
            }
        
        if not page_ids:
            logger.warning(f"[Bulk] No pages found in space '{space_key}'")
            return {
                "total": 0,
                "processed": 0,
                "success": 0,
                "errors": 0,
                "dry_run": dry_run,
                "details": [{
                    "space_key": space_key,
                    "status": "error",
                    "message": "No pages found in space",
                    "tags": None
                }]
            }
        
        logger.info(f"[Bulk] Found {len(page_ids)} pages in space '{space_key}'")
        return await self.tag_pages(page_ids, dry_run=dry_run)
