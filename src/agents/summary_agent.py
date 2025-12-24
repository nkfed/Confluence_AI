from typing import Dict, Any
from .base_agent import BaseAgent
from src.clients.confluence_client import ConfluenceClient
from src.clients.openai_client import OpenAIClient
from src.utils.html_to_text import html_to_text
from src.utils.token_counter import estimate_tokens_count
from src.core.logging.logger import get_logger, audit_logger
from src.core.logging.timing import log_timing

logger = get_logger(__name__)


class SummaryAgent(BaseAgent):
    """Агент, який формує summary для сторінок Confluence."""

    def __init__(self, confluence_client: ConfluenceClient = None, openai_client: OpenAIClient = None):
        super().__init__()
        self.confluence = confluence_client or ConfluenceClient()
        self.ai = openai_client or OpenAIClient()

    @log_timing
    async def generate_summary(self, page_id: str) -> str:
        """
        Повний пайплайн генерації summary згідно з кроками логування.
        """
        logger.info(f"Step 1: Fetching Confluence page (page_id={page_id})")
        page = self.confluence.get_page(page_id)

        html_content = page.get("body", {}).get("storage", {}).get("value", "")
        logger.info(f"Step 2: Converting HTML to text (html_length={len(html_content)})")

        text = html_to_text(html_content)
        logger.info(f"Step 2.1: Text extracted (text_length={len(text)})")

        logger.info("Step 3: Estimating tokens")
        approx_tokens = estimate_tokens_count(text)
        logger.info(f"Step 3.1: Estimated tokens = {approx_tokens}")

        logger.info("Step 4: Building prompt for OpenAI")
        prompt = (
            "Зроби структуроване, лаконічне та професійне summary для наступного тексту. "
            "Виділи ключові тези, рішення, ризики, залежності та наступні кроки. "
            "Форматуй результат у вигляді зрозумілих блоків.\n\n"
            f"Текст:\n{text[:5000]}"
        )

        logger.info("Step 5: Calling OpenAI")
        summary = await self.ai.generate(prompt)

        logger.info("Step 6: Summary generated successfully")
        return summary

    async def process_page(self, page_id: str) -> Dict[str, Any]:
        """
        Обгортка над generate_summary для отримання додаткових метаданих.
        """
        # Отримуємо сторінку ще раз для title, або можна було б передати її з generate_summary.
        # Але згідно з шаблоном, generate_summary сам фетчить сторінку.
        # Щоб не фетчити двічі, ми можемо трохи змінити логіку, 
        # але завдання вимагає саме такий generate_summary.
        
        # Для отримання title спочатку фетчимо (або беремо з generate_summary, якщо змінити його)
        page = self.confluence.get_page(page_id)
        title = page.get("title")
        
        summary = await self.generate_summary(page_id)
        
        # Отримуємо оцінку токенів (можемо взяти з тексту знову, або передати через контекст)
        html_body = page.get("body", {}).get("storage", {}).get("value", "")
        clean_text = html_to_text(html_body)
        token_estimate = estimate_tokens_count(clean_text)

        return {
            "page_id": page_id,
            "title": title,
            "summary": summary,
            "summary_tokens_estimate": token_estimate
        }

    async def update_page_with_summary(self, page_id: str) -> Dict[str, Any]:
        """
        Оновлює сторінку Confluence, додаючи summary внизу.
        """
        audit_logger.info(
            f"action=update_page_with_summary page_id={page_id} mode={self.mode} started"
        )

        self.enforce_page_policy(page_id)

        result = await self.process_page(page_id)

        summary_html = (
            "<h2>AI Summary</h2>"
            f"<p>{result['summary'].replace('\n', '<br>')}</p>"
        )

        updated_page = self.confluence.append_to_page(
            page_id=page_id,
            html_block=summary_html
        )

        audit_logger.info(
            f"action=update_page_with_summary page_id={page_id} mode={self.mode} status=success"
        )

        return {
            "status": "updated",
            "page_id": page_id,
            "title": result["title"],
            "summary_added": True,
            "summary_tokens_estimate": result["summary_tokens_estimate"]
        }