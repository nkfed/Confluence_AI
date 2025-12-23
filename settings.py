import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Клас для керування налаштуваннями проєкту через .env."""

    def __init__(self):
        # Confluence
        self.CONFLUENCE_BASE_URL: str | None = os.getenv("CONFLUENCE_BASE_URL")
        self.CONFLUENCE_EMAIL: str | None = os.getenv("CONFLUENCE_EMAIL")
        self.CONFLUENCE_API_TOKEN: str | None = os.getenv("CONFLUENCE_API_TOKEN")

        # OpenAI
        self.OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY")
        self.OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o")

        # API
        self.API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
        self.API_PORT: int = int(os.getenv("API_PORT", 8000))
        self.DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"

        # Валідація критичних змінних
        self._validate()

    def _validate(self):
        """Перевіряє наявність критичних змінних середовища."""
        missing = []

        if not self.OPENAI_API_KEY:
            missing.append("OPENAI_API_KEY")

        if not self.CONFLUENCE_BASE_URL:
            missing.append("CONFLUENCE_BASE_URL")

        if not self.CONFLUENCE_EMAIL:
            missing.append("CONFLUENCE_EMAIL")

        if not self.CONFLUENCE_API_TOKEN:
            missing.append("CONFLUENCE_API_TOKEN")

        if missing:
            raise EnvironmentError(
                f"Відсутні необхідні змінні середовища: {', '.join(missing)}"
            )


settings = Settings()
