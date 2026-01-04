import asyncio
import time
from typing import Optional, Dict, List
from uuid import uuid4
from datetime import datetime
from src.services.tagging_service import TaggingService, flatten_tags
from src.services.tagging_context import prepare_ai_context
from src.clients.confluence_client import ConfluenceClient
from src.core.ai.router import router
from src.core.ai.optimization_patch_v2 import get_optimization_patch_v2
from src.core.logging.logger import get_logger
from settings import settings
from fastapi import HTTPException

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

    async def tag_pages(self, page_ids: list[str], space_key: str, dry_run: bool = None, task_id: str = None, skip_whitelist_filter: bool = False) -> dict:
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
            skip_whitelist_filter: If True, skip whitelist filtering (used by tag_space)
        
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
        
        # ✅ Strict mode: process only explicitly provided page_ids (no other sources)
        unique_page_ids = list(dict.fromkeys(page_ids))
        duplicates_removed = len(page_ids) - len(unique_page_ids)
        if duplicates_removed > 0:
            logger.info(f"[TagPages] Removed {duplicates_removed} duplicate page_ids")

        pages_to_process = unique_page_ids  # do not append children/ancestors/related pages
        
        # ✅ Whitelist integration (STRICT, NO TREE TRAVERSAL)
        whitelist_manager = WhitelistManager()
        try:
            # Use entry points only; DO NOT traverse children to avoid extra Confluence calls
            allowed_ids = {int(x) for x in whitelist_manager.get_entry_points(space_key)}
            logger.info(
                f"[WHITELIST] Loaded entry points for space={space_key}: {len(allowed_ids)} entries (no recursion)"
            )
            logger.debug(f"[TagPages] Allowed IDs (first 20): {sorted(list(allowed_ids))[:20]}")

            if not allowed_ids:
                logger.error(f"[TagPages] No whitelist entries for space {space_key}")
                raise HTTPException(
                    status_code=403,
                    detail=f"No whitelist entries for space {space_key}. Add entries to whitelist_config.json"
                )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"[TagPages] Failed to load whitelist: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to load whitelist: {str(e)}"
            )
        
        # ✅ Filter page_ids by whitelist (except when skip_whitelist_filter=True for tag_space)
        page_ids_int = [int(pid) for pid in pages_to_process]
        
        if skip_whitelist_filter:
            # tag_space mode: process ALL pages without whitelist filtering
            filtered_ids = page_ids_int
            logger.info(f"[TagPages] skip_whitelist_filter=True (tag_space mode): processing all {len(filtered_ids)} pages (no whitelist filter)")
        else:
            # ALL other modes (TEST/SAFE_TEST/PROD): filter by whitelist
            filtered_ids = [pid for pid in page_ids_int if pid in allowed_ids]
            logger.info(
                f"[TagPages] Whitelist filtering (mode={mode}): "
                f"requested={len(pages_to_process)}, allowed={len(allowed_ids)}, filtered={len(filtered_ids)}"
            )
            
            if not filtered_ids:
                logger.error(f"[TagPages] No pages allowed by whitelist")
                raise HTTPException(
                    status_code=403,
                    detail="No pages allowed by whitelist. Check whitelist_config.json"
                )
        
        results = []
        success_count = 0
        skipped_due_to_whitelist = len(pages_to_process) - len(filtered_ids)
        error_count = 0

        logger.info(
            f"[TagPages] Processing {len(filtered_ids)} allowed pages "
            f"(mode={mode}, effective_dry_run={effective_dry_run}, skipped={skipped_due_to_whitelist})"
        )

        # Apply micro-batching to reduce concurrent pressure on rate-limited APIs
        patch = get_optimization_patch_v2()
        batches = patch.micro_batch(filtered_ids)
        logger.info(f"[TagPages] Micro-batching: {len(filtered_ids)} pages into {len(batches)} batches of ~2")
        
        # Process filtered pages with micro-batching
        for batch_idx, batch in enumerate(batches, 1):
            logger.debug(f"[TagPages] Processing batch {batch_idx}/{len(batches)} with {len(batch)} pages")
            
            for page_id_int in batch:
                # ✅ Перевірка чи не зупинено процес
                if task_id and not ACTIVE_TASKS.get(task_id, True):
                    logger.info(f"[TagPages] Task {task_id} stopped by user, breaking loop")
                    break
                
                page_id = str(page_id_int)
                try:
                    logger.info(f"[TagPages] Processing page {page_id} (effective_dry_run={effective_dry_run})")
                    
                    # Завантажуємо контент сторінки
                    page = await self.confluence.get_page(page_id, expand="body.storage")
                    if not page:
                        logger.warning(f"[TagPages] Page {page_id} not found")
                        error_count += 1
                        results.append({
                            "page_id": page_id,
                            "status": "error",
                            "message": "Page not found"
                        })
                        continue
                    
                    html = page.get("body", {}).get("storage", {}).get("value", "")
                    text = prepare_ai_context(html)
                    
                    # Формуємо індивідуальний AI-промпт на основі контенту
                    logger.info(f"[TagPages] Calling TaggingAgent via router for page {page_id}")
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
                        # У TEST режимі всі оновлення заборонені (навіть для whitelist сторінок)
                        status = "forbidden" if mode == "TEST" else "dry_run"
                        logger.info(f"[TagPages] [{status.upper()}] Would add labels for {page_id}: {list(to_add)}")
                        success_count += 1
                        results.append({
                            "page_id": page_id,
                            "status": status,
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
            
            # Small pause between batches to avoid burst traffic
            if batch_idx < len(batches):
                logger.debug(f"[TagPages] Batch {batch_idx} complete, pausing 0.5s before next batch")
                await asyncio.sleep(0.5)

        # Final result
        logger.info(f"[TagPages] Tagging completed: {success_count} success, {error_count} errors, {skipped_due_to_whitelist} skipped")
        
        # Collect patch metrics
        patch_stats = patch.get_statistics()
        logger.info(
            f"[TagPages] Patch v2.0 metrics: "
            f"Gemini success={patch_stats.get('gemini_success_rate', 'N/A')}, "
            f"fallback={patch_stats.get('fallback_rate', 'N/A')}, "
            f"avg_duration={patch_stats.get('avg_duration_ms', 'N/A')}ms"
        )
        
        return {
            "total": len(pages_to_process),
            "processed": len(filtered_ids),
            "success": success_count,
            "errors": error_count,
            "skipped_by_whitelist": skipped_due_to_whitelist,
            "duplicates_removed": duplicates_removed,
            "mode": mode,
            "dry_run": effective_dry_run,
            "whitelist_enabled": True,
            "patch_metrics": patch_stats,
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
        from src.agents.summary_agent import SummaryAgent
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
            # ✅ ВАЖЛИВО: Для tag_tree, нам потрібна лише перевірка, чи root_page_id є в entry_points,
            # НЕ всі дочірні сторінки від усіх entry_points (це робить _collect_all_children)
            entry_points = whitelist_manager.get_entry_points(space_key)
            allowed_ids = set(entry_points)
            allowed_ids_str = {str(pid) for pid in allowed_ids}
            
            logger.info(
                 f"[WHITELIST] Loaded entry points for space={space_key}: {len(allowed_ids_str)} entries"
            )
            logger.debug(
                f"[TagTree] Entry point IDs (first 20): {sorted(list(allowed_ids_str))[:20]}"
            )
            
            if not allowed_ids:
                logger.error(f"[TagTree] No whitelist entry points for space {space_key}")
                return {
                    "status": "error",
                    "message": f"No whitelist entries for space {space_key}. Add entries to whitelist_config.json",
                    "total": 0,
                    "processed": 0,
                    "success": 0,
                    "errors": 1
                }
            
            # Перевірка що root_page_id в whitelist entry points (крім PROD режиму)
            if mode != "PROD":  # ✅ PROD дозволяє будь-які root_page_id
                logger.info(
                    f"[WHITELIST] Checking root_id={root_page_id} against whitelist entry points"
                )
                if str(root_page_id) not in allowed_ids_str:
                    logger.error(
                        f"[TagTree] Root page {root_page_id} not in whitelist entry points for space {space_key}"
                    )
                    return {
                        "status": "error",
                        "message": f"Root page {root_page_id} is not an allowed entry point for space {space_key}",
                        "total": 0,
                        "processed": 0,
                        "success": 0,
                        "errors": 1,
                        "whitelist_enabled": True,
                        "root_page_allowed": False
                    }
            else:
                logger.info(f"[TagTree] PROD mode - skipping root_page_id whitelist check for {root_page_id}")
            
            logger.info(f"[TagTree] Root page {root_page_id} is in whitelist entry points - allowed")
            
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
        
        # ✅ ВАЖЛИВО: Для tag_tree без section-based filtering, 
        # передаємо пустий список - це означає "без обмеження на теги"
        allowed_labels: List[str] = []
        logger.info("[tag-tree] Using unbounded tag set (allowed_labels=[]) - all proposed tags allowed")
        
        # Step 3: Collect all pages in tree
        logger.info(f"[TagTree] Collecting page tree from root {root_page_id}")
        all_page_ids = await self._collect_all_children(root_page_id)
        logger.info(f"[TagTree] Collected {len(all_page_ids)} total pages in tree")
        
        # ✅ ВАЖЛИВО: У tag_tree, дочірні сторінки автоматично дозволені 
        # (бо вони підпорядковані дозволеному root_page_id)
        # Перевіряється лише root_page_id - дочірні не потребують окремої перевірки
        pages_to_process = all_page_ids  # Усі дочірні дозволені як частина дерева
        skipped_by_whitelist = 0
        logger.info(f"[TagTree] Processing all {len(pages_to_process)} pages in tree (all children allowed by root_page_id)")
        
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
                text_content = prepare_ai_context(html_content)
                logger.debug(f"[tag-tree] Extracted {len(text_content)} chars of text")
                
                # Generate tags with dynamic whitelist filtering (already deduplicated in agent)
                # Fallback to section tags if content is too short or contains only links
                logger.info(
                    f"[TagTree] Calling SummaryAgent.generate_tags_for_tree via router for page {page_id}",
                    extra={"page_id": page_id, "allowed_labels_count": len(allowed_labels)}
                )
                suggested_tags = await summary_agent.generate_tags_for_tree(
                    content=text_content,
                    allowed_labels=allowed_labels,
                    dry_run=effective_dry_run,
                    page_id=page_id
                )
                # suggested_tags are already deduplicated and filtered by generate_tags_for_tree
                logger.info(f"[TagTree] Generated {len(suggested_tags)} filtered tags: {suggested_tags}")
                
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
            f"total_pages={len(all_page_ids)} "
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
        
        # ✅ ВАЖЛИВО: tag_space обробляє ВСІ сторінки спейсу - whitelist НЕ використовується!
        # На відміну від tag_pages, tag_tree, auto_tag_page - tag_space призначений для повної
        # обробки будь-якого спейсу без обмежень, це пакетний режим для адміністраторів
        logger.info(
            f"[TagSpace] tag_space mode: processing ALL pages in space (NO whitelist filtering)"
        )
        
        # ✅ Обгортаємо всю логіку у try/finally для гарантованого очищення
        try:
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
                    "whitelist_enabled": False,
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
                    "whitelist_enabled": False,
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
            
            # ✅ ВАЖЛИВО: tag_space обробляє ВСІ сторінки спейсу БЕЗ whitelist фільтрації!
            # На відміну від tag_pages, tag_tree тощо - tag_space призначений для повної
            # обробки будь-якого спейсу, whitelist тут не використовується
            pages_to_process = page_ids
            skipped_by_whitelist = 0
            
            logger.info(
                f"[TagSpace] Processing all {len(pages_to_process)} pages in space without whitelist filtering. "
                f"Mode={mode}, effective_dry_run={effective_dry_run}"
            )
            
            # ✅ Перевірка що є сторінки до обробки
            if not pages_to_process:
                logger.error(f"[TagSpace] No pages found to process in space {space_key}")
                return {
                    "task_id": task_id,
                    "status": "error",
                    "message": f"No pages in space {space_key}",
                    "total": 0,
                    "processed": 0,
                    "success": 0,
                    "errors": 0,
                    "skipped_by_whitelist": 0,
                    "dry_run": effective_dry_run,
                    "mode": mode,
                    "whitelist_enabled": False,
                    "details": []
                }
            
            # Обробка сторінок БЕЗ whitelist фільтрації
            result = await self.tag_pages(
                pages_to_process, 
                space_key=space_key,
                dry_run=effective_dry_run,
                task_id=task_id,
                skip_whitelist_filter=True  # ✅ tag_space обробляє ВСІ сторінки!
            )
            
            # Додаємо інформацію про task_id
            result["task_id"] = task_id
            result["skipped_by_whitelist"] = 0  # Для tag_space whitelist не використовується
            result["mode"] = mode
            result["whitelist_enabled"] = False  # tag_space не використовує whitelist
            
            # Зберігаємо результат у реєстрі
            RESULTS_REGISTRY[task_id] = result
            
            # ✅ Логуємо завершення
            logger.info(f"[TagSpace] Task {task_id} completed successfully")
            
            response = {
                "task_id": task_id,
                "total": len(page_ids),
                "processed": result['processed'],  # ✅ Already an int from tag_pages
                "success": result['success'],       # ✅ Already an int
                "errors": result['errors'],         # ✅ Already an int
                "skipped_by_whitelist": 0,  # ✅ Для tag_space = 0 (whitelist не використовується)
                "dry_run": effective_dry_run,
                "mode": mode,
                "whitelist_enabled": False,  # tag_space не використовує whitelist
                "details": result['details']
            }

            return response
            
        finally:
            # ✅ Гарантоване очищення ресурсів навіть при помилках
            ACTIVE_TASKS.pop(task_id, None)
            TASK_PROGRESS.pop(task_id, None)
            
            # Записуємо timestamp завершення (якщо існує)
            if task_id in TASK_TIMESTAMPS:
                TASK_TIMESTAMPS[task_id]["finish"] = datetime.utcnow().isoformat()
            
            logger.info(f"[TagSpace] Task {task_id} cleaned up (removed from ACTIVE_TASKS and TASK_PROGRESS)")
    async def read_tags(
        self,
        space_key: str,
        root_id: Optional[str] = None,
        tag_substrings: Optional[str] = None
    ) -> dict:
        """
        Read current tags on pages in a space or subtree.
        
        Args:
            space_key: Confluence space key
            root_id: Optional root page ID to read only descendants
            tag_substrings: Optional comma-separated list of substrings to filter tags
                           (e.g., "doc,domain,kb" will match any tag containing these)
        
        Returns:
            {
                "total": int,
                "processed": int,
                "no_tags": int,
                "errors": int,
                "details": [
                    {
                        "page_id": str,
                        "title": str,
                        "existing_tags": List[str]
                    }
                ]
            }
        """
        logger.info(
            f"[ReadTags] Starting read_tags for space={space_key}, "
            f"root_id={root_id}, tag_substrings={tag_substrings}"
        )
        
        # Parse tag substrings if provided
        substrings = []
        if tag_substrings:
            substrings = [s.strip() for s in tag_substrings.split(",") if s.strip()]
            logger.info(f"[ReadTags] Filtering by tag substrings: {substrings}")
        
        # Determine which pages to read
        if root_id:
            logger.info(f"[ReadTags] Collecting page tree from root {root_id}")
            page_ids = await self._collect_all_children(root_id)
            logger.info(f"[ReadTags] Collected {len(page_ids)} pages in tree")
        else:
            logger.info(f"[ReadTags] Reading all pages in space {space_key}")
            page_ids = await self.confluence.get_all_pages_in_space(space_key)
            logger.info(f"[ReadTags] Found {len(page_ids)} pages in space")
        
        results = []
        no_tags_count = 0
        error_count = 0
        
        for i, page_id in enumerate(page_ids, 1):
            try:
                logger.debug(f"[ReadTags] Processing page {i}/{len(page_ids)}: {page_id}")
                
                # Get page info
                page = await self.confluence.get_page(page_id)
                if not page:
                    logger.warning(f"[ReadTags] Page {page_id} not found")
                    error_count += 1
                    continue
                
                page_title = page.get("title", "Unknown")
                
                # Get current tags
                existing_tags = await self.confluence.get_labels(page_id)
                
                # Apply substring filter if provided
                if substrings:
                    filtered_tags = [
                        tag for tag in existing_tags
                        if any(sub.lower() in tag.lower() for sub in substrings)
                    ]
                else:
                    filtered_tags = existing_tags
                
                # Count pages with no matching tags
                if not filtered_tags:
                    no_tags_count += 1
                    logger.debug(f"[ReadTags] Page {page_id} has no matching tags")
                    # Still add to results even if no tags
                
                # Add to results (always)
                results.append({
                    "page_id": page_id,
                    "title": page_title,
                    "existing_tags": filtered_tags
                })
                
                logger.debug(f"[ReadTags] Page {page_id}: {len(filtered_tags)} tags")
                
            except Exception as e:
                logger.error(f"[ReadTags] Error processing page {page_id}: {e}")
                error_count += 1
        
        logger.info(
            f"[ReadTags] Completed: processed={len(page_ids)}, "
            f"with_tags={len(results)}, no_tags={no_tags_count}, errors={error_count}"
        )
        
        return {
            "total": len(page_ids),
            "processed": len(page_ids),
            "no_tags": no_tags_count,
            "errors": error_count,
            "details": results
        }