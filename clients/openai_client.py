from typing import Optional
from openai import OpenAI
from settings import settings


class OpenAIClient:
    """Клієнт для роботи з OpenAI API."""

    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_MODEL or "gpt-4o"

    def generate(self, prompt: str, system_prompt: str = "You are a helpful AI assistant.") -> str:
        """
        Універсальний метод для генерації тексту.
        Повертає текстову відповідь моделі.
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2
            )

            # Новий формат відповіді OpenAI SDK
            return response.choices[0].message.content

        except Exception as e:
            raise RuntimeError(f"OpenAI API error: {e}")

    def summarize(self, text: str) -> str:
        """Згенерувати summary для довгого тексту."""
        prompt = (
            "Стисло та структуровано підсумуй наступний текст. "
            "Виділи ключові тези, рішення, ризики та наступні кроки.\n\n"
            f"Текст:\n{text}"
        )
        return self.generate(prompt)