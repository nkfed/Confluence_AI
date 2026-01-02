from src.agents.summary_agent import SummaryAgent
import asyncio
import pytest


class DummyAIClient:
    """
    Простий тестовий AI-клієнт, який повертає передбачуваний результат,
    щоб не викликати реальний OpenAI API під час тестів.
    """

    async def generate(self, prompt: str) -> str:
        return "Тестовий summary для перевірки роботи SummaryAgent."


@pytest.mark.skip(reason="Requires mocking Confluence client")
async def test_summary_agent_generate_summary_with_plain_text():
    """
    Перевіряємо, що SummaryAgent:
    - коректно викликає AI-клієнт
    - повертає рядок
    - не падає на простому вхідному тексті
    
    NOTE: This test requires mocking the Confluence client to work properly
    """
    agent = SummaryAgent()
    # Підміняємо реальний OpenAIClient на тестовий DummyAIClient
    agent.ai = DummyAIClient()

    input_text = "Це тестовий текст для перевірки роботи агента."
    result = await agent.generate_summary(input_text)

    assert isinstance(result, str)
    assert "тестовий summary" in result.lower()


if __name__ == "__main__":
    asyncio.run(test_summary_agent_generate_summary_with_plain_text())