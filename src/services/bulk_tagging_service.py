import asyncio
import time
from typing import Optional, Dict
from uuid import uuid4
from datetime import datetime
from src.services.tagging_service import TaggingService, flatten_tags
from src.clients.confluence_client import ConfluenceClient
from src.core.ai.router import router
from src.core.logging.logger import get_logger
from settings import settings

logger = get_logger(__name__)

# Глобальний реєстр активних задач для можливості зупинки
ACTIVE_TASKS = {}

# Глобальний реєстр результатів завершених задач
RESULTS_REGISTRY: Dict[str, dict] = {}

# Глобальний реєстр прогресу виконання задач
TASK_PROGRESS: Dict[str, Dict[str, int]] = {}

# Глобальний реєстр часових міток задач
TASK_TIMESTAMPS: Dict[str, Dict[str, str]] = {}

class BulkTaggingService:
    def __init__(self, confluence_client: ConfluenceClient = None, tagging_service: TaggingService = None):
        self.confluence = confluence_client or ConfluenceClient()
        self.tagging_service = tagging_service or TaggingService(confluence_client=self.confluence)
        
        # Create agent instance for mode/policy checking (use router for AI logging)
        from src.agents.tagging_agent import TaggingAgent
        self.agent = TaggingAgent(ai_router=router)
    
    def create_task_id(self) -> str:
        """
        Create a new task ID and register it in ACTIVE_TASKS.
        
        Returns:
            Generated task ID (hex string)
        """
        task_id = uuid4().hex
        ACTIVE_TASKS[task_id] = True
        TASK_TIMESTAMPS[task_id] = {"start": datetime.utcnow().isoformat(), "finish": None}
        logger.info(f"[BulkTaggingService] Created task {task_id}")
        return task_id

    async def tag_pages(self, page_ids: list[str], space_key: str, dry_run: bool = None, task_id: str = None) -> dict:
        """
        Bulk tag multiple pages with unified whitelist and режимна матриця enforcement.
        
        Режимна матриця:
        - TEST: завжди dry-run (effective_dry_run=True), тільки whitelist сторінки
        - SAFE_TEST: dry_run керується параметром, тільки whitelist сторінки
        - PROD: dry_run керується параметром, тільки whitelist сторінки
        
        Args:
            page_ids: List of Confluence page IDs
            space_key: Confluence space key (required for whitelist lookup)
            dry_run: If True, performs dry-run. Ignored in TEST mode (always dry-run)
            task_id: Optional task ID for cancellation support
        
        Returns:
            Dictionary with tagging results including whitelist filtering info
        """
        from src.core.whitelist.whitelist_manager import WhitelistManager
        
        mode = self.agent.mode
        
        # ✅ Визначення ефективного dry_run на основі режиму (як у tag-tree і tag-space)
        if mode == "TEST":
            effective_dry_run = True
            logger.info(f"[TagPages] TEST mode - forcing dry_run=True (received dry_run={dry_run})")
        elif mode == "SAFE_TEST":
            effective_dry_run = dry_run if dry_run is not None else True
            logger.info(f"[TagPages] SAFE_TEST mode - dry_run={effective_dry_run}")
        elif mode == "PROD":
            effective_dry_run = dry_run if dry_run is not None else True
            logger.info(f"[TagPages] PROD mode - dry_run={effective_dry_run}")
        else:
            effective_dry_run = True
            logger.warning(f"[TagPages] Unknown mode '{mode}' - defaulting to dry_run=True")
        
        logger.info(
            f"[TagPages] Starting tag-pages for space_key={space_key}, "
            f"mode={mode}, dry_run_param={dry_run}, effective_dry_run={effective_dry_run}"
        )
        
        # ✅ Remove duplicates while preserving order
        unique_page_ids = list(dict.fromkeys(page_ids))
        duplicates_removed = len(page_ids) - len(unique_page_ids)
        
        if duplicates_removed > 0:
            logger.info(f"[TagPages] Removed {duplicates_removed} duplicate page_ids")
        
        page_ids = unique_page_ids
        
        # ✅ Whitelist integration - load allowed IDs
        whitelist_manager = WhitelistManager()
        
        try:
            allowed_ids = await whitelist_manager.get_allowed_ids(space_key, self.confluence)
            logger.info(
                f"[TagPages] Whitelist loaded: {len(allowed_ids)} allowed pages for {space_key}"
            )
            logger.debug(f"[TagPages] Allowed IDs (first 20): {sorted(list(allowed_ids))[:20]}")
            
            if not allowed_ids:
                logger.error(f"[TagPages] No whitelist entries for space {space_key}")
                from fastapi import HTTPException
                raise HTTPException(
                    status_code=403,
                    detail=f"No whitelist entries for space {space_key}. Add entries to whitelist_config.json"
                )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"[TagPages] Failed to load whitelist: {e}")
            from fastapi import HTTPException
            raise HTTPException(
                status_code=500,
                detail=f"Failed to load whitelist: {str(e)}"
            )
        
        # ✅ Filter page_ids by whitelist
        page_ids_int = [int(pid) for pid in page_ids]
        filtered_ids = [pid for pid in page_ids_int if pid in allowed_ids]
        
        logger.info(
            f"[TagPages] Whitelist filtering: "
            f"requested={len(page_ids)}, allowed={len(allowed_ids)}, filtered={len(filtered_ids)}"
        )
        
        if not filtered_ids:
            logger.error(f"[TagPages] No pages allowed by whitelist")
            from fastapi import HTTPException
            raise HTTPException(
                status_code=403,
                detail="No pages allowed by whitelist. Check whitelist_config.json"
            )
        
        results = []
        success_count = 0
        skipped_due_to_whitelist = len(page_ids) - len(filtered_ids)
        error_count = 0

        logger.info(
            f"[TagPages] Processing {len(filtered_ids)} allowed pages "
            f"(mode={mode}, effective_dry_run={effective_dry_run}, skipped={skipped_due_to_whitelist})"
        )

        # Process filtered pages only
        for page_id_int in filtered_ids:
            # ✅ Перевірка чи не зупинено процес
            if task_id and not ACTIVE_TASKS.get(task_id, True):
                logger.info(f"[TagPages] Task {task_id} stopped by user, breaking loop")
                break
            
            page_id = str(page_id_int)
            try:
                logger.info(f"[TagPages] Processing page {page_id} (effective_dry_run={effective_dry_run})")
                
                # Завантажуємо контент сторінки
                page = await self.confluence.get_page(page_id)
                if not page:
                    logger.warning(f"[TagPages] Page {page_id} not found")
                    error_count += 1
                    results.append({
                        "page_id": page_id,
                        "status": "error",
                        "message": "Page not found"
                    })
                    continue
                
                text = page.get("body", {}).get("storage", {}).get("value", "")
                logger.debug(f"[TagPages] Extracted {len(text)} chars from page {page_id}")
                
                # Формуємо індивідуальний AI-промпт на основі контенту
                from src.agents.tagging_agent import TaggingAgent
                agent = TaggingAgent(ai_router=router)
                tags = await agent.suggest_tags(text)
                
                logger.info(f"[TagPages] Generated tags for {page_id}: {tags}")
                
                # Flatten tags and compare with existing
                flat_tags = flatten_tags(tags)
                logger.debug(f"[TagPages] Flattened tags: {flat_tags}")
                
                # Get existing labels
                existing_labels = await self.confluence.get_labels(page_id)
                logger.debug(f"[TagPages] Existing labels: {existing_labels}")
                
                # Calculate differences
                proposed = set(flat_tags)
                existing = set(existing_labels)
                to_add = proposed - existing
                
                logger.info(f"[TagPages] Tag comparison for {page_id}: proposed={len(proposed)}, existing={len(existing)}, to_add={len(to_add)}")
                
                # Використовуємо effective_dry_run для перевірки режиму
                if effective_dry_run:
                    logger.info(f"[TagPages] [DRY-RUN] Would add labels for {page_id}: {list(to_add)}")
                    success_count += 1
                    results.append({
                        "page_id": page_id,
                        "status": "dry_run",
                        "tags": {
                            "proposed": list(proposed),
                            "existing": list(existing),
                            "added": [],
                            "to_add": list(to_add)
                        },
                        "dry_run": True
                    })
                    continue
                
                # Real update mode: page is already in whitelist (filtered_ids)
                if to_add:
                    logger.info(f"[TagPages] Updating labels for page {page_id}: adding {list(to_add)}")
                    await self.confluence.update_labels(page_id, list(to_add))
                    logger.info(f"[TagPages] Successfully updated labels for page {page_id}")
                else:
                    logger.info(f"[TagPages] No new labels to add for page {page_id}")
                
                success_count += 1
                results.append({
                    "page_id": page_id,
                    "status": "updated",
                    "tags": {
                        "proposed": list(proposed),
                        "existing": list(existing),
                        "added": list(to_add),
                        "to_add": []
                    },
                    "dry_run": False
                })

            except Exception as e:
                logger.error(f"[TagPages] Failed to process page {page_id}: {e}")
                error_count += 1
                results.append({
                    "page_id": page_id,
                    "status": "error",
                    "message": str(e),
                    "tags": None
                })
            
            # ✅ Оновити прогрес після обробки сторінки
            if task_id and task_id in TASK_PROGRESS:
                TASK_PROGRESS[task_id]["processed"] += 1

            # Throttling
            await asyncio.sleep(0.3)

        # Final result
        logger.info(f"[TagPages] Tagging completed: {success_count} success, {error_count} errors, {skipped_due_to_whitelist} skipped")
        
        return {
            "total": len(page_ids),
            "processed": len(filtered_ids),
            "success": success_count,
            "errors": error_count,
            "skipped_by_whitelist": skipped_due_to_whitelist,
            "duplicates_removed": duplicates_removed,
            "mode": mode,
            "dry_run": effective_dry_run,
            "whitelist_enabled": True,
            "details": results
        }

    async def tag_tree(self, root_page_id: str, space_key: str, dry_run: bool = False) -> dict:
        """
        Tags entire documentation tree with whitelist control.
        
        Architecture with WhitelistManager:
        1. Load whitelist from whitelist_config.json for space_key
        2. Verify root_page_id is in allowed_ids
        3. Collect all children in tree
        4. Filter tree nodes through allowed_ids
        5. For each allowed page: generate tags and update
        
        Args:
            root_page_id: Root page ID of the documentation tree
            space_key: Space key for whitelist lookup (required)
            dry_run: If True, only simulate tagging without updating Confluence
            
        Returns:
            Dictionary with tagging results
        """
        from src.sections.section_detector import detect_section, detect_section_safe
        from src.sections.whitelist import get_allowed_labels, get_default_labels
        from src.agents.summary_agent import SummaryAgent
        from src.utils.html_to_text import html_to_text
        from src.core.whitelist.whitelist_manager import WhitelistManager
        
        mode = self.agent.mode
        
        # ✅ Визначення ефективного dry_run на основі режиму (уніфіковано з tag_pages/tag_space)
        if mode == "TEST":
            effective_dry_run = True
            logger.info(f"[TagTree] TEST mode - forcing dry_run=True (received dry_run={dry_run})")
        elif mode == "SAFE_TEST":
            effective_dry_run = dry_run if dry_run is not None else True
            logger.info(f"[TagTree] SAFE_TEST mode - dry_run={effective_dry_run}")
        elif mode == "PROD":
            effective_dry_run = dry_run if dry_run is not None else True
            logger.info(f"[TagTree] PROD mode - dry_run={effective_dry_run}")
        else:
            effective_dry_run = True
            logger.warning(f"[TagTree] Unknown mode '{mode}' - defaulting to dry_run=True")
        
        logger.info(
            f"[TagTree] Starting tag-tree for root_page_id={root_page_id}, "
            f"mode={mode}, dry_run_param={dry_run}, effective_dry_run={effective_dry_run}, space_key={space_key}"
        )
        
        # ✅ Whitelist integration (завжди обов'язковий для tag-tree)
        whitelist_manager = WhitelistManager()
        whitelist_enabled = True
        
        logger.info(f"[TagTree] Whitelist enabled for space={space_key}")
        try:
            allowed_ids = await whitelist_manager.get_allowed_ids(space_key, self.confluence)
            logger.info(
                f"[TagTree] Whitelist loaded: {len(allowed_ids)} allowed pages for {space_key}"
            )
            logger.debug(
                f"[TagTree] Allowed IDs (first 20): {sorted(list(allowed_ids))[:20]}"
            )
            
            if not allowed_ids:
                logger.error(f"[TagTree] No whitelist entries for space {space_key}")
                return {
                    "status": "error",
                    "message": f"No whitelist entries for space {space_key}. Add entries to whitelist_config.json",
                    "total": 0,
                    "processed": 0,
                    "success": 0,
                    "errors": 1
                }
            
            # Перевірка що root_page_id в whitelist
            root_page_id_int = int(root_page_id)
            if root_page_id_int not in allowed_ids:
                logger.error(
                    f"[TagTree] Root page {root_page_id} not in whitelist for space {space_key}"
                )
                return {
                    "status": "error",
                    "message": f"Root page {root_page_id} is not allowed by whitelist for space {space_key}",
                    "total": 0,
                    "processed": 0,
                    "success": 0,
                    "errors": 1,
                    "whitelist_enabled": True,
                    "root_page_allowed": False
                }
            
            logger.info(f"[TagTree] Root page {root_page_id} is in whitelist - allowed")
            
        except Exception as e:
            logger.error(f"[TagTree] Failed to load whitelist: {e}")
            return {
                "status": "error",
                "message": f"Failed to load whitelist: {str(e)}",
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
        logger.info(f"[TagTree] Collecting page tree from root {root_page_id}")
        all_page_ids = await self._collect_all_children(root_page_id)
        logger.info(f"[TagTree] Collected {len(all_page_ids)} total pages in tree")
        
        # ✅ NEW: Filter by whitelist
        if whitelist_enabled and allowed_ids is not None:
            pages_to_process = []
            skipped_by_whitelist = 0
            
            for page_id in all_page_ids:
                page_id_int = int(page_id)
                if page_id_int in allowed_ids:
                    pages_to_process.append(page_id)
                else:
                    skipped_by_whitelist += 1
            
            logger.info(
                f"[TagTree] After whitelist filter: {len(pages_to_process)} to process, "
                f"{skipped_by_whitelist} skipped (not in whitelist)"
            )
        else:
            pages_to_process = all_page_ids
            skipped_by_whitelist = 0
            logger.info(f"[TagTree] No whitelist filter - processing all {len(all_page_ids)} pages")
        
        # Step 4: Process each page
        results = []
        success_count = 0
        error_count = 0
        skipped_count = 0
        
        # Use router-based SummaryAgent to ensure AI calls are logged via log_ai_call
        summary_agent = SummaryAgent(ai_router=router)
        
        for i, page_id in enumerate(pages_to_process, 1):
            logger.info(f"[TagTree] Processing page {i}/{len(pages_to_process)}: {page_id}")
            
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
                    dry_run=effective_dry_run,
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
                
                # Update labels (if not effective_dry_run and there are changes)
                if not effective_dry_run and has_changes:
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
                elif effective_dry_run and has_changes:
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
                        dry_run=effective_dry_run
                    ),
                    "dry_run": effective_dry_run
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
            f"tag_tree_operation root_page_id={root_page_id} space_key={space_key} "
            f"section={section} total_pages={len(all_page_ids)} "
            f"processed={len(pages_to_process)} skipped_by_whitelist={skipped_by_whitelist} "
            f"success={success_count} errors={error_count} "
            f"skipped={skipped_count} dry_run={effective_dry_run} mode={mode} whitelist_enabled={whitelist_enabled}"
        )
        
        logger.info(
            f"[TagTree] Completed: {success_count} success, {error_count} errors, "
            f"{skipped_count} skipped, {skipped_by_whitelist} filtered by whitelist"
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
            "space_key": space_key,
            "total": len(all_page_ids),
            "processed": len(pages_to_process),
            "skipped_by_whitelist": skipped_by_whitelist,
            "success": success_count,
            "errors": error_count,
            "skipped_count": skipped_count,
            "dry_run": effective_dry_run,
            "mode": mode,
            "whitelist_enabled": whitelist_enabled,
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

    async def tag_space(self, space_key: str, dry_run: Optional[bool] = None, task_id: str = None) -> dict:
        """
        Tag all pages in a Confluence space using AI with centralized whitelist support.
        
        Режимна матриця з whitelist:
        - TEST: завжди dry_run=True + тільки whitelist сторінки
        - SAFE_TEST: dry_run керується параметром + тільки whitelist сторінки
        - PROD: dry_run керується параметром + тільки whitelist сторінки
        
        Args:
            space_key: Confluence space key
            dry_run: If True, performs dry-run. Ignored in TEST mode (always dry-run)
            task_id: Task ID for cancellation support (provided by background task)
            
        Returns:
            {
                "task_id": str,
                "total": int,
                "processed": int,
                "success": int,
                "errors": int,
                "skipped_by_whitelist": int,
                "dry_run": bool,
                "mode": str,
                "whitelist_enabled": bool,
                "details": [...]
            }
        """
        from src.core.whitelist import WhitelistManager
        
        # ✅ Використання task_id з параметру (або створення нового)
        if task_id is None:
            task_id = self.create_task_id()
        else:
            logger.info(f"[TagSpace] Using existing task {task_id} for space {space_key}")
        
        mode = self.agent.mode
        
        # ✅ Уніфікована dry_run матриця (як у tag_pages і tag_tree)
        if mode == "TEST":
            effective_dry_run = True
            logger.info(f"[TagSpace] TEST mode - forcing dry_run=True (received dry_run={dry_run})")
        elif mode == "SAFE_TEST":
            effective_dry_run = dry_run if dry_run is not None else True
            logger.info(f"[TagSpace] SAFE_TEST mode - dry_run={effective_dry_run}")
        elif mode == "PROD":
            effective_dry_run = dry_run if dry_run is not None else True
            logger.info(f"[TagSpace] PROD mode - dry_run={effective_dry_run}")
        else:
            effective_dry_run = True
            logger.warning(f"[TagSpace] Unknown mode '{mode}' - defaulting to dry_run=True")
        
        logger.info(
            f"[TagSpace] Starting tag-space for space_key={space_key}, "
            f"mode={mode}, dry_run_param={dry_run}, effective_dry_run={effective_dry_run}"
        )
        
        # ✅ Обгортаємо всю логіку у try/finally для гарантованого очищення
        try:
            # Ініціалізація WhitelistManager
            whitelist_manager = WhitelistManager()
            
            # ✅ Whitelist завжди застосовується для tag-space
            whitelist_enabled = True
            
            logger.info(
                f"[TagSpace] Using whitelist for scope in mode={mode}, effective_dry_run={effective_dry_run}. "
                f"Whitelist controls which pages are processed, dry_run controls whether to write."
            )
            
            # Завантаження дозволених ID (завжди для tag-space)
            try:
                allowed_ids = await whitelist_manager.get_allowed_ids(space_key, self.confluence)
                logger.info(
                    f"[TagSpace] Whitelist loaded: {len(allowed_ids)} allowed pages for {space_key}"
                )
                logger.debug(
                    f"[TagSpace] Allowed IDs (first 20): {sorted(list(allowed_ids))[:20]}"
                )
                
                if not allowed_ids:
                    logger.warning(
                        f"[TagSpace] No whitelist entries found for {space_key}. "
                        f"Configure whitelist in whitelist_config.json to process pages."
                    )
                    return {
                        "task_id": task_id,
                        "total": 0,
                        "processed": 0,
                        "success": 0,
                        "errors": 0,
                        "skipped_by_whitelist": 0,
                        "dry_run": effective_dry_run,
                        "mode": mode,
                        "whitelist_enabled": whitelist_enabled,
                        "details": [{
                            "space_key": space_key,
                            "status": "error",
                            "message": f"No whitelist entries for space {space_key}. Add entries to whitelist_config.json",
                            "tags": None
                        }]
                    }
            except Exception as e:
                logger.error(f"[TagSpace] Failed to load whitelist: {e}")
                return {
                    "task_id": task_id,
                    "total": 0,
                    "processed": 0,
                    "success": 0,
                    "errors": 1,
                    "skipped_by_whitelist": 0,
                    "dry_run": effective_dry_run,
                    "mode": mode,
                    "whitelist_enabled": whitelist_enabled,
                    "details": [{
                        "space_key": space_key,
                        "status": "error",
                        "message": f"Failed to load whitelist: {str(e)}",
                        "tags": None
                    }]
                }
            
            # Завантаження всіх сторінок простору
            logger.info(f"[tag-space] Fetching all pages in space '{space_key}'")
            
            try:
                page_ids = await self.confluence.get_all_pages_in_space(space_key)
            except Exception as e:
                logger.error(f"[tag-space] Failed to fetch pages from space '{space_key}': {e}")
                return {
                    "task_id": task_id,
                    "total": 0,
                    "processed": 0,
                    "success": 0,
                    "errors": 1,
                    "skipped_by_whitelist": 0,
                    "dry_run": effective_dry_run,
                    "mode": mode,
                    "whitelist_enabled": whitelist_enabled,
                    "details": [{
                        "space_key": space_key,
                        "status": "error",
                        "message": f"Failed to fetch pages: {str(e)}",
                        "tags": None
                    }]
                }
            
            if not page_ids:
                logger.warning(f"[tag-space] No pages found in space '{space_key}'")
                return {
                    "task_id": task_id,
                    "total": 0,
                    "processed": 0,
                    "success": 0,
                    "errors": 0,
                    "skipped_by_whitelist": 0,
                    "dry_run": effective_dry_run,
                    "mode": mode,
                    "whitelist_enabled": whitelist_enabled,
                    "details": [{
                        "space_key": space_key,
                        "status": "error",
                        "message": "No pages found in space",
                        "tags": None
                    }]
                }
            
            logger.info(f"[TagSpace] Found {len(page_ids)} total pages in space '{space_key}'")
            
            # ✅ Ініціалізуємо прогрес
            TASK_PROGRESS[task_id] = {"total": len(page_ids), "processed": 0}
            
            # Фільтрація за whitelist (завжди для tag-space)
            pages_to_process = []
            skipped_by_whitelist = 0
            
            for page_id in page_ids:
                page_id_int = int(page_id)
                
                # Завжди перевіряємо whitelist для tag-space
                if whitelist_manager.is_allowed(space_key, page_id_int, allowed_ids):
                    pages_to_process.append(page_id)
                else:
                    skipped_by_whitelist += 1
            
            logger.info(
                f"[TagSpace] After whitelist filter: {len(pages_to_process)} to process, "
                f"{skipped_by_whitelist} skipped. "
                f"Mode={mode}, effective_dry_run={effective_dry_run}"
            )
            
            # ✅ Перевірка що є сторінки після whitelist-фільтрації
            if not pages_to_process:
                logger.error(
                    f"[TagSpace] No pages allowed by whitelist for space {space_key}. "
                    f"Total pages: {len(page_ids)}, all filtered by whitelist."
                )
                return {
                    "task_id": task_id,
                    "status": "error",
                    "message": f"No pages allowed by whitelist for space {space_key}",
                    "total": len(page_ids),
                    "processed": 0,
                    "success": 0,
                    "errors": 0,
                    "skipped_by_whitelist": len(page_ids),
                    "dry_run": effective_dry_run,
                    "mode": mode,
                    "whitelist_enabled": True,
                    "details": []
                }
            
            # Обробка сторінок з передачею allowed_ids (завжди передаємо для tag-space)
            result = await self.tag_pages(
                pages_to_process, 
                space_key=space_key,
                dry_run=effective_dry_run,
                task_id=task_id
            )
            
            # Додаємо інформацію про whitelist та task_id
            result["task_id"] = task_id
            result["skipped_by_whitelist"] = skipped_by_whitelist
            result["mode"] = mode
            result["whitelist_enabled"] = whitelist_enabled
            
            # Зберігаємо результат у реєстрі
            RESULTS_REGISTRY[task_id] = result
            
            # ✅ Логуємо завершення
            logger.info(f"[TagSpace] Task {task_id} completed successfully")
            
            return result
            
        finally:
            # ✅ Гарантоване очищення ресурсів навіть при помилках
            ACTIVE_TASKS.pop(task_id, None)
            TASK_PROGRESS.pop(task_id, None)
            
            # Записуємо timestamp завершення (якщо існує)
            if task_id in TASK_TIMESTAMPS:
                TASK_TIMESTAMPS[task_id]["finish"] = datetime.utcnow().isoformat()
            
            logger.info(f"[TagSpace] Task {task_id} cleaned up (removed from ACTIVE_TASKS and TASK_PROGRESS)")
