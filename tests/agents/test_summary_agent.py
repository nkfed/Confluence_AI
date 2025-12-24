from src.agents.summary_agent import SummaryAgent


class DummyAIClient:
    """
    Простий тестовий AI-клієнт, який повертає передбачуваний результат,
    щоб не викликати реальний OpenAI API під час тестів.
    """

    def generate(self, prompt: str) -> str:
        return "Тестовий summary для перевірки роботи SummaryAgent."


def test_summary_agent_generate_summary_with_plain_text():
    """
    Перевіряємо, що SummaryAgent:
    - коректно викликає AI-клієнт
    - повертає рядок
    - не падає на простому вхідному тексті
    """
    agent = SummaryAgent()
    # Підміняємо реальний OpenAIClient на тестовий DummyAIClient
    agent.ai = DummyAIClient()

    input_text = "Це тестовий текст для перевірки роботи агента."
    result = agent.generate_summary(input_text)

    assert isinstance(result, str)
    assert "тестовий summary" in result.lower()