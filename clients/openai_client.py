from openai import OpenAI
from settings import settings


class OpenAIClient:
    """Клієнт для роботи з OpenAI API."""

    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_MODEL or "gpt-4o"

    def generate(self, prompt: str) -> str:
        """Універсальний метод для генерації тексту."""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a helpful AI assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2
        )
        return response.choices[0].message.content

    def summarize(self, text: str) -> str:
        """Згенерувати summary для довгого тексту."""
        prompt = (
            "Стисло та структуровано підсумуй наступний текст. "
            "Виділи ключові тези, рішення, ризики та наступні кроки.\n\n"
            f"Текст:\n{text}"
        )
        return self.generate(prompt)