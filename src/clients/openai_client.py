from typing import Optional
from openai import AsyncOpenAI
from settings import settings
from src.core.logging.logger import get_logger
from src.core.logging.timing import log_timing
from src.core.logging.retry import log_retry

logger = get_logger(__name__)


class OpenAIClient:
    """Клієнт для роботи з OpenAI API."""

    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_MODEL or "gpt-4o"

    @log_retry(attempts=3, backoff=2.0)
    @log_timing
    async def generate(self, prompt: str, system_prompt: str = "You are a helpful AI assistant.") -> str:
        """
        Універсальний метод для генерації тексту.
        Повертає текстову відповідь моделі.
        """
        logger.info(f"Sending request to OpenAI (model: {self.model})")
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2
            )

            # Новий формат відповіді OpenAI SDK
            logger.info("Received response from OpenAI")
            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise RuntimeError(f"OpenAI API error: {e}")

    async def summarize(self, text: str) -> str:
        """Згенерувати summary для довгого тексту."""
        prompt = (
            "Стисло та структуровано підсумуй наступний текст. "
            "Виділи ключові тези, рішення, ризики та наступні кроки.\n\n"
            f"Текст:\n{text}"
        )
        return await self.generate(prompt)