import asyncio
from typing import Optional
from openai import AsyncOpenAI
from settings import settings
from src.core.logging.logger import get_logger
from src.core.logging.timing import log_timing

logger = get_logger(__name__)


class OpenAIClient:
    """Клієнт для роботи з OpenAI API."""

    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = "gpt-5-mini"

    @log_timing
    async def generate(self, prompt: str):
        max_retries = 5
        delay = 1  # seconds

        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"[OpenAI] Attempt {attempt}/{max_retries}")
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                )
                return response.choices[0].message.content

            except Exception as e:
                error_text = str(e)

                # Rate limit (429)
                if "rate_limit" in error_text or "429" in error_text:
                    logger.warning(f"[OpenAI] Rate limit hit on attempt {attempt}: {e}")

                    if attempt == max_retries:
                        logger.error("[OpenAI] Max retries reached, giving up")
                        raise RuntimeError(f"OpenAI rate limit error after {max_retries} attempts: {e}")

                    logger.info(f"[OpenAI] Waiting {delay}s before retry...")
                    await asyncio.sleep(delay)
                    delay *= 2
                    continue

                # Інші помилки — пробросити далі
                logger.error(f"[OpenAI] Unexpected error: {e}")
                raise RuntimeError(f"OpenAI API error: {e}")

    async def summarize(self, text: str) -> str:
        """Згенерувати summary для довгого тексту."""
        prompt = (
            "Стисло та структуровано підсумуй наступний текст. "
            "Виділи ключові тези, рішення, ризики та наступні кроки.\n\n"
            f"Текст:\n{text}"
        )
        return await self.generate(prompt)