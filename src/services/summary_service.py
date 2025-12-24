from typing import Dict, Any
from agents.summary_agent import SummaryAgent


class SummaryService:
    """
    Сервіс для роботи з summary сторінок Confluence.
    Інкапсулює логіку виклику агента та допоміжні речі
    (логування, подальше розширення).
    """

    def __init__(self) -> None:
        """Ініціалізує сервіс та створює екземпляр SummaryAgent."""
        self.agent = SummaryAgent()

    def summarize_page(self, page_id: str) -> Dict[str, Any]:
        """
        Повний цикл:
        - викликає SummaryAgent для отримання summary
        - повертає структурований словник з метаданими
        """
        result = self.agent.process_page(page_id)

        if not result:
            raise ValueError(f"Не вдалося отримати сторінку {page_id}")

        return {
            "page_id": result.get("page_id", page_id),
            "title": result.get("title"),
            "summary": result.get("summary", ""),
            "summary_tokens_estimate": result.get("summary_tokens_estimate", 0),
        }

    def summarize_and_update_page(self, page_id: str) -> Dict[str, Any]:
        """
        Використовує метод агента для оновлення сторінки в Confluence
        (якщо реалізований update_page_with_summary в SummaryAgent).
        """
        if not hasattr(self.agent, "update_page_with_summary"):
            raise NotImplementedError(
                "Метод update_page_with_summary відсутній у SummaryAgent."
            )

        update_result = self.agent.update_page_with_summary(page_id)

        return {
            "page_id": update_result.get("page_id", page_id),
            "title": update_result.get("title"),
            "status": update_result.get("status"),
            "summary_added": update_result.get("summary_added", False),
            "summary_tokens_estimate": update_result.get("summary_tokens_estimate", 0),
        }