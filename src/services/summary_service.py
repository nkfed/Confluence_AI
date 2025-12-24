from typing import Dict, Any
from src.agents.summary_agent import SummaryAgent
from src.core.logging.logger import get_logger
from src.core.logging.timing import log_timing

logger = get_logger(__name__)


class SummaryService:
    """
    Сервіс для роботи з summary сторінок Confluence.
    Інкапсулює логіку виклику агента та допоміжні речі
    (логування, подальше розширення).
    """

    def __init__(self) -> None:
        """Ініціалізує сервіс та створює екземпляр SummaryAgent."""
        self.agent = SummaryAgent()

    @log_timing
    async def summarize_page(self, page_id: str) -> Dict[str, Any]:
        """
        Повний цикл:
        - викликає SummaryAgent для отримання summary
        - повертає структурований словник з метаданими
        """
        logger.info(f"SummaryService.summarize_page called for page_id: {page_id}")
        result = await self.agent.process_page(page_id)

        if not result:
            logger.error(f"Failed to process page {page_id}")
            raise ValueError(f"Не вдалося отримати сторінку {page_id}")

        logger.info(f"Successfully summarized page {page_id}")

        return {
            "page_id": result.get("page_id", page_id),
            "title": result.get("title"),
            "summary": result.get("summary", ""),
            "summary_tokens_estimate": result.get("summary_tokens_estimate", 0),
        }

    @log_timing
    async def summarize_and_update_page(self, page_id: str) -> Dict[str, Any]:
        """
        Використовує метод агента для оновлення сторінки в Confluence
        (якщо реалізований update_page_with_summary в SummaryAgent).
        """
        logger.info(f"SummaryService.summarize_and_update_page called for page_id: {page_id}")

        if not hasattr(self.agent, "update_page_with_summary"):
            raise NotImplementedError(
                "Метод update_page_with_summary відсутній у SummaryAgent."
            )

        update_result = await self.agent.update_page_with_summary(page_id)

        logger.info(f"Successfully updated page {page_id}")

        return {
            "page_id": update_result.get("page_id", page_id),
            "title": update_result.get("title"),
            "status": update_result.get("status"),
            "summary_added": update_result.get("summary_added", False),
            "summary_tokens_estimate": update_result.get("summary_tokens_estimate", 0),
        }