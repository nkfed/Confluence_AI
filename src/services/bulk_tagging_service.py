import asyncio
import time
from src.services.tagging_service import TaggingService
from src.clients.confluence_client import ConfluenceClient
from src.core.logging.logger import get_logger

logger = get_logger(__name__)

class BulkTaggingService:
    def __init__(self, confluence_client: ConfluenceClient = None, tagging_service: TaggingService = None):
        self.confluence = confluence_client or ConfluenceClient()
        self.tagging_service = tagging_service or TaggingService(confluence_client=self.confluence)

    async def tag_pages(self, page_ids: list[str], dry_run: bool = False) -> dict:
        """
        Проходить по списку сторінок і викликає TaggingService.auto_tag_page()
        """
        results = []
        success_count = 0
        skipped_count = 0
        error_count = 0

        logger.info(f"[Bulk] Starting tagging for {len(page_ids)} pages (dry_run={dry_run})")

        for page_id in page_ids:
            try:
                logger.info(f"[Bulk] Tagging page {page_id} (dry_run={dry_run})")
                res = await self.tagging_service.auto_tag_page(page_id, dry_run=dry_run)
                
                # TaggingService повертає status="ok", але ConfluenceClient міг пропустити через whitelist
                # Ми можемо перевірити audit_status, який прокидається з ConfluenceClient
                audit_status = res.get("audit_status")
                
                if audit_status == "success":
                    success_count += 1
                elif audit_status == "skipped":
                    skipped_count += 1
                else:
                    # Якщо статус не success і не skipped, але TaggingService повернув ok
                    # це може бути специфічний випадок (наприклад, сторінку не знайдено)
                    if res.get("status") == "error":
                        error_count += 1
                    else:
                        success_count += 1 # Вважаємо за успіх, якщо немає явних ознак пропуску/помилки

                results.append({
                    "page_id": page_id,
                    "status": res.get("status"),
                    "audit_status": audit_status,
                    "tags": res.get("tags")
                })

            except Exception as e:
                logger.error(f"[Bulk] Failed to tag page {page_id}: {e}")
                error_count += 1
                results.append({
                    "page_id": page_id,
                    "status": "error",
                    "message": str(e)
                })

            # Throttling
            await asyncio.sleep(0.3)

        return {
            "total": len(page_ids),
            "success": success_count,
            "skipped": skipped_count,
            "errors": error_count,
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
