import asyncio
import time
from src.services.tagging_service import TaggingService
from src.clients.confluence_client import ConfluenceClient
from src.core.logging.logger import get_logger
from settings import settings

logger = get_logger(__name__)

class BulkTaggingService:
    def __init__(self, confluence_client: ConfluenceClient = None, tagging_service: TaggingService = None):
        self.confluence = confluence_client or ConfluenceClient()
        self.tagging_service = tagging_service or TaggingService(confluence_client=self.confluence)

    async def tag_pages(self, page_ids: list[str], dry_run: bool = False) -> dict:
        """
        Проходить по списку сторінок і викликає TaggingService.auto_tag_page()
        
        Оптимізована логіка:
        - Якщо dry_run=False: обробляє тільки сторінки з whitelist
        - Якщо dry_run=True: обробляє всі сторінки (для тестування)
        """
        results = []
        success_count = 0
        skipped_due_to_whitelist = 0
        error_count = 0

        logger.info(f"[Bulk] Starting tagging for {len(page_ids)} pages (dry_run={dry_run})")

        # 1. Отримуємо whitelist зі settings
        
        allowed_pages = [x.strip() for x in settings.ALLOWED_TAGGING_PAGES.split(",")]
        
        # 2. Розділяємо page_ids на дві групи
        allowed_ids = [pid for pid in page_ids if pid in allowed_pages]
        skipped_ids = [pid for pid in page_ids if pid not in allowed_pages]
        
        logger.info(f"[Bulk] Pages breakdown: {len(allowed_ids)} allowed, {len(skipped_ids)} in whitelist filter")
        logger.info(f"[Bulk] Allowed pages: {allowed_ids}")
        logger.info(f"[Bulk] Skipped pages (not in whitelist): {skipped_ids}")

        # 3. Обробка skipped_ids залежно від dry_run
        if not dry_run:
            # У production режимі НЕ викликаємо AI для skipped_ids
            logger.info(f"[Bulk] Production mode: skipping {len(skipped_ids)} pages not in whitelist")
            for page_id in skipped_ids:
                skipped_due_to_whitelist += 1
                results.append({
                    "page_id": page_id,
                    "status": "skipped_due_to_whitelist",
                    "message": "Page not in ALLOWED_TAGGING_PAGES whitelist",
                    "tags": None
                })
        else:
            # У dry-run режимі обробляємо всі сторінки для тестування
            logger.info(f"[Bulk] Dry-run mode: processing all {len(skipped_ids)} skipped pages for testing")
            for page_id in skipped_ids:
                try:
                    logger.info(f"[Bulk] [DRY-RUN] Processing skipped page {page_id}")
                    
                    # Завантажуємо контент
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
                    
                    # Викликаємо AI для генерації тегів
                    from src.agents.tagging_agent import TaggingAgent
                    agent = TaggingAgent()
                    tags = await agent.suggest_tags(text)
                    
                    logger.info(f"[Bulk] [DRY-RUN] Generated tags for {page_id}: {tags}")
                    
                    skipped_due_to_whitelist += 1
                    results.append({
                        "page_id": page_id,
                        "status": "skipped_due_to_whitelist",
                        "message": "Page not in whitelist (processed in dry-run for testing)",
                        "tags": tags,
                        "dry_run": True
                    })
                    
                except Exception as e:
                    logger.error(f"[Bulk] [DRY-RUN] Failed to process skipped page {page_id}: {e}")
                    error_count += 1
                    results.append({
                        "page_id": page_id,
                        "status": "error",
                        "message": str(e)
                    })
                
                # Throttling
                await asyncio.sleep(0.3)

        # 4. Обробка allowed_ids (сторінки з whitelist)
        logger.info(f"[Bulk] Processing {len(allowed_ids)} allowed pages")
        for page_id in allowed_ids:
            try:
                logger.info(f"[Bulk] Processing allowed page {page_id} (dry_run={dry_run})")
                
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
                
                # Оновлюємо labels у Confluence (якщо не dry_run)
                if not dry_run:
                    logger.info(f"[Bulk] Updating labels for page {page_id}")
                    await self.confluence.update_labels(page_id, tags, dry_run=False)
                    logger.info(f"[Bulk] Successfully updated labels for page {page_id}")
                else:
                    logger.info(f"[Bulk] [DRY-RUN] Would update labels for {page_id}: {tags}")
                
                success_count += 1
                results.append({
                    "page_id": page_id,
                    "status": "success",
                    "tags": tags,
                    "dry_run": dry_run
                })

            except Exception as e:
                logger.error(f"[Bulk] Failed to process allowed page {page_id}: {e}")
                error_count += 1
                results.append({
                    "page_id": page_id,
                    "status": "error",
                    "message": str(e)
                })

            # Throttling
            await asyncio.sleep(0.3)

        # 5. Фінальний результат
        logger.info(f"[Bulk] Tagging completed: {success_count} success, {skipped_due_to_whitelist} skipped, {error_count} errors")
        
        return {
            "total": len(page_ids),
            "processed": len(allowed_ids),
            "skipped_due_to_whitelist": skipped_due_to_whitelist,
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
        from src.sections.section_detector import detect_section
        from src.sections.whitelist import get_allowed_labels
        from src.agents.summary_agent import SummaryAgent
        from src.utils.html_to_text import html_to_text
        
        logger.info(f"[tag-tree] Starting tag-tree operation for root_page_id={root_page_id} (dry_run={dry_run})")
        
        # Step 1: Detect section
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
                elif dry_run and has_changes:
                    logger.info(f"[tag-tree] [DRY-RUN] Would update labels for {page_id}")
                    status = "dry_run"
                    skipped = False
                else:
                    logger.info(f"[tag-tree] No label changes needed for page {page_id} - SKIPPED")
                    status = "no_changes"
                    skipped = True
                    skipped_count += 1
                
                success_count += 1
                results.append({
                    "page_id": page_id,
                    "title": page_title,
                    "status": status,
                    "skipped": skipped,
                    "suggested_tags": suggested_tags,
                    "current_labels": current_labels,
                    "labels_to_add": labels_to_add,
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

    async def tag_space(self, space_key: str, dry_run: bool = False) -> dict:
        """
        Тегує всі сторінки у вказаному просторі.
        """
        logger.info(f"[Bulk] Fetching all pages in space {space_key}")
        page_ids = await self.confluence.get_all_pages_in_space(space_key)
        
        return await self.tag_pages(page_ids, dry_run=dry_run)
