from src.agents.tagging_agent import TaggingAgent
from src.clients.confluence_client import ConfluenceClient
from src.services.tagging_audit import TaggingAuditService
from src.core.logging.logger import get_logger

logger = get_logger(__name__)

class TaggingService:
    def __init__(self, confluence_client: ConfluenceClient = None, tagging_agent: TaggingAgent = None):
        self.confluence = confluence_client or ConfluenceClient()
        self.agent = tagging_agent or TaggingAgent()
        self.audit = TaggingAuditService()

    async def auto_tag_page(self, page_id: str, dry_run: bool = False) -> dict:
        """
        1. Завантажує сторінку з Confluence
        2. Витягує текст
        3. Викликає TaggingAgent
        4. Оновлює теги (якщо не dry_run)
        5. Логує зміни в аудит
        6. Повертає результат
        """

        logger.info(f"[TaggingService] Fetching page {page_id}")
        page = await self.confluence.get_page(page_id)

        if not page:
            logger.error(f"[TaggingService] Page {page_id} not found")
            return {"status": "error", "message": "Page not found"}

        text = page.get("body", {}).get("storage", {}).get("value", "")
        logger.debug(f"[TaggingService] Extracted text length: {len(text)}")

        logger.info(f"[TaggingService] Calling TaggingAgent for page {page_id}")
        tags = await self.agent.suggest_tags(text)

        logger.info(f"[TaggingService] Suggested tags: {tags}")

        logger.info(f"[TaggingService] Updating labels for page {page_id} (dry_run={dry_run})")
        
        # Виконуємо оновлення та отримуємо деталі змін
        result = await self.confluence.update_labels(page_id, tags, dry_run=dry_run)

        # Логуємо в аудит
        self.audit.log_change(
            page_id=page_id,
            old_labels=result["old_labels"],
            new_labels=result["new_labels"],
            to_add=result["to_add"],
            to_remove=result["to_remove"],
            dry_run=dry_run,
            status=result["status"]
        )

        return {
            "status": "ok",
            "tags": tags,
            "dry_run": dry_run,
            "audit_status": result["status"]
        }
