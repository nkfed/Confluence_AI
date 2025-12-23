from settings import settings
from clients.confluence_client import ConfluenceClient
from clients.openai_client import OpenAIClient


def test_confluence():
    print("\n=== TEST: Confluence Client ===")
    client = ConfluenceClient()

    # Рекомендовано зберігати page_id у .env
    page_id = settings.TEST_PAGE_ID if hasattr(settings, "TEST_PAGE_ID") else None

    if not page_id:
        print("⚠️ TEST_PAGE_ID не заданий у .env — пропускаємо тест Confluence.")
        return

    try:
        page = client.get_page(page_id)
        print("✅ Title:", page.get("title"))
        print("✅ Version:", page["version"]["number"])

        body_preview = client.get_page_body(page_id)[:120]
        print("✅ Body preview:", body_preview + "...")
    except Exception as e:
        print("❌ Confluence error:", e)


def test_openai():
    print("\n=== TEST: OpenAI Client ===")
    client = OpenAIClient()

    try:
        result = client.summarize("Це тестовий текст для перевірки роботи OpenAI клієнта.")
        print("AI summary:", result)
    except Exception as e:
        print("❌ OpenAI error:", e)


def main():
    print("🔧 DEBUG mode active")
    print("🔑 OPENAI_API_KEY:", settings.OPENAI_API_KEY[:8] + "...")

    test_confluence()
    test_openai()

    print("\n🎉 Усі тести виконано!")


if __name__ == "__main__":
    main()