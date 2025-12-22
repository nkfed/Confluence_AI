class BaseAgent:
    """Базовий клас для AI-агентів."""
    def __init__(self, api_key, model):
        self.api_key = api_key
        self.model = model

    def run_query(self, prompt, context):
        """Відправка запиту до LLM."""
        pass
