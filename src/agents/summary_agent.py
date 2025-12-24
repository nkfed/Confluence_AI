from typing import Dict, Any
from .base_agent import BaseAgent
from clients.confluence_client import ConfluenceClient
from clients.openai_client import OpenAIClient
from utils.html_to_text import html_to_text
from utils.token_counter import estimate_tokens_count


class SummaryAgent(BaseAgent):
    """Агент, який формує summary для сторінок Confluence."""

    def __init__(self):
        super().__init__()
        self.confluence = ConfluenceClient()
        self.ai = OpenAIClient()

    def generate_summary(self, page_content: str) -> str:
        """
        Приймає HTML-контент сторінки Confluence,
        конвертує його у текст, формує промпт і повертає summary.
        """

        clean_text = html_to_text(page_content)

        if not clean_text.strip():
            return "Сторінка порожня або не містить текстового контенту."

        prompt = (
            "Зроби структуроване, лаконічне та професійне summary для наступного тексту. "
            "Виділи ключові тези, рішення, ризики, залежності та наступні кроки. "
            "Форматуй результат у вигляді зрозумілих блоків.\n\n"
            f"Текст:\n{clean_text}"
        )

        return self.ai.generate(prompt)

    def process_page(self, page_id: str) -> Dict[str, Any]:
        """
        Повний пайплайн:
        1. Отримати сторінку з Confluence
        2. Витягнути HTML-контент
        3. Очистити HTML → текст
        4. Порахувати токени
        5. Згенерувати summary
        6. Повернути структурований результат
        """

        page = self.confluence.get_page(page_id)

        title = page.get("title")
        html_body = page.get("body", {}).get("storage", {}).get("value", "")

        clean_text = html_to_text(html_body)
        token_estimate = estimate_tokens_count(clean_text)
        """
        print("CLEAN TEXT:\n", clean_text[:500])
        print("TOKEN ESTIMATE:", token_estimate)
        """
        summary = self.generate_summary(html_body)

        return {
            "page_id": page_id,
            "title": title,
            "summary": summary,
            "summary_tokens_estimate": token_estimate
        }

    def update_page_with_summary(self, page_id: str) -> Dict[str, Any]:
        """
        Оновлює сторінку Confluence, додаючи summary внизу.
        """

        result = self.process_page(page_id)

        summary_html = (
            "<h2>AI Summary</h2>"
            f"<p>{result['summary'].replace('\n', '<br>')}</p>"
        )

        updated_page = self.confluence.append_to_page(
            page_id=page_id,
            html_block=summary_html
        )

        return {
            "status": "updated",
            "page_id": page_id,
            "title": result["title"],
            "summary_added": True,
            "summary_tokens_estimate": result["summary_tokens_estimate"]
        }