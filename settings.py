import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    """Клас для керування налаштуваннями проєкту через .env."""
    
    # Confluence
    CONFLUENCE_URL = os.getenv("CONFLUENCE_URL")
    CONFLUENCE_USER_EMAIL = os.getenv("CONFLUENCE_USER_EMAIL")
    CONFLUENCE_API_TOKEN = os.getenv("CONFLUENCE_API_TOKEN")
    
    # OpenAI
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4")
    
    # API
    API_HOST = os.getenv("API_HOST", "0.0.0.0")
    API_PORT = int(os.getenv("API_PORT", 8000))
    DEBUG = os.getenv("DEBUG", "True").lower() == "true"

settings = Settings()
