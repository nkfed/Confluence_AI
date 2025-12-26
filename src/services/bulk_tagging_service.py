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
        Викликає тегування для кореневої сторінки та всіх її нащадків.
        """
        logger.info(f"[Bulk] Collecting tree for root page {root_page_id}")
        
        # Збираємо всі ID (корінь + діти)
        # Для справжнього дерева потрібна рекурсія, але інструкція каже "get_child_pages" 
        # і "формує повний список сторінок дерева".
        # Зробимо простий рівень вкладеності або рекурсивний збір.
        
        all_ids = await self._collect_all_children(root_page_id)
        
        return await self.tag_pages(all_ids, dry_run=dry_run)

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
