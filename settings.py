import os
from enum import Enum
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()

class AgentMode(str, Enum):
    """
    Режими роботи агентів:
    - TEST: dry-run режим, жодних змін у Confluence
    - SAFE_TEST: оновлення тільки whitelist сторінок
    - PROD: повний доступ до всіх сторінок
    """
    TEST = "TEST"
    SAFE_TEST = "SAFE_TEST"
    PROD = "PROD"

def _env(name: str, default: str):
    """
    Хелпер: повертає значення зі змінної середовища,
    або дефолт, якщо змінної немає.
    """
    return os.getenv(name, default)

class Settings(BaseSettings):
    """Клас для керування налаштуваннями проєкту через .env."""
    CONFLUENCE_BASE_URL: str
    CONFLUENCE_EMAIL: str
    CONFLUENCE_API_TOKEN: str

    # OpenAI
    OPENAI_API_KEY: str
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o")

    # API
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", 8000))
    DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_JSON: bool = os.getenv("LOG_JSON", "False").lower() == "true"
    LOG_DIR: str = os.getenv("LOG_DIR", "logs")

    # --- GLOBAL MODE ---
    AGENT_MODE: str = _env("AGENT_MODE", AgentMode.TEST)

    # --- INDIVIDUAL AGENT MODES ---
    SUMMARY_AGENT_MODE: str = _env("SUMMARY_AGENT_MODE", AGENT_MODE)
    TAGGING_AGENT_MODE: str = _env("TAGGING_AGENT_MODE", AGENT_MODE)
    CLASSIFICATION_AGENT_MODE: str = _env("CLASSIFICATION_AGENT_MODE", AGENT_MODE)
    QUALITY_AUDIT_AGENT_MODE: str = _env("QUALITY_AUDIT_AGENT_MODE", AGENT_MODE)
    CONFLUENCE_SYNC_AGENT_MODE: str = _env("CONFLUENCE_SYNC_AGENT_MODE", AGENT_MODE)
    BACKLOG_ANALYSIS_AGENT_MODE: str = _env("BACKLOG_ANALYSIS_AGENT_MODE", AGENT_MODE)
    REQUIREMENTS_AGENT_MODE: str = _env("REQUIREMENTS_AGENT_MODE", AGENT_MODE)
    REFACTORING_AGENT_MODE: str = _env("REFACTORING_AGENT_MODE", AGENT_MODE)
    IMAGE_OPTIMIZATION_AGENT_MODE: str = _env("IMAGE_OPTIMIZATION_AGENT_MODE", AGENT_MODE)
    SECURITY_AUDIT_AGENT_MODE: str = _env("SECURITY_AUDIT_AGENT_MODE", AGENT_MODE)
    PIPELINE_AGENT_MODE: str = _env("PIPELINE_AGENT_MODE", AGENT_MODE)
    CONTENT_REWRITE_AGENT_MODE: str = _env("CONTENT_REWRITE_AGENT_MODE", AGENT_MODE)

    # --- TEST PAGE IDS ---
    ALLOWED_TAGGING_PAGES: str = _env("ALLOWED_TAGGING_PAGES", "19713687690,19713687700")
    SUMMARY_AGENT_TEST_PAGE: str = _env("SUMMARY_AGENT_TEST_PAGE", "19713687690")
    TAGGING_AGENT_TEST_PAGE: str = _env("TAGGING_AGENT_TEST_PAGE", "19713687690")
    CLASSIFICATION_AGENT_TEST_PAGE: str = _env("CLASSIFICATION_AGENT_TEST_PAGE", "19713687690")
    QUALITY_AUDIT_AGENT_TEST_PAGE: str = _env("QUALITY_AUDIT_AGENT_TEST_PAGE", "19713687690")

    class Config:
        env_file = ".env"
        extra = "allow"

settings = Settings()
