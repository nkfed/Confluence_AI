import uvicorn
from settings import settings
from clients.confluence_client import ConfluenceClient


def test_confluence():
    """Тестовий виклик Confluence API для перевірки авторизації та структури відповіді."""
    client = ConfluenceClient()

    # Заміни на реальний page_id з Confluence
    page_id = "19721289759"

    try:
        page = client.get_page(page_id)
        print("✅ Title:", page.get("title"))
        print("✅ Version:", page["version"]["number"])
        print("✅ Body:", page["body"]["storage"]["value"][:100] + "...")
    except Exception as e:
        print("❌ Confluence error:", e)


def main():
    """Точка входу для CLI‑тестів або запуску FastAPI."""
    if settings.DEBUG:
        print("🔧 DEBUG mode active")
        print("🔑 OPENAI_API_KEY:", settings.OPENAI_API_KEY[:8] + "...")
        test_confluence()

    print("🚀 Starting FastAPI server...")
    uvicorn.run(
        "api.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG
    )


if __name__ == "__main__":
    main()
