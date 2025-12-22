from settings import settings
from clients.confluence_client import ConfluenceClient
from clients.openai_client import OpenAIClient


def test_confluence():
    print("\n=== TEST: Confluence Client ===")
    client = ConfluenceClient()
    page_id = "19721289759"  # твій реальний page_id

    try:
        page = client.get_page(page_id)
        print("✅ Title:", page.get("title"))
        print("✅ Version:", page["version"]["number"])
        print("✅ Body:", page["body"]["storage"]["value"][:120] + "...")
    except Exception as e:
        print("❌ Confluence error:", e)


def test_openai():
    print("\n=== TEST: OpenAI Client ===")
    client = OpenAIClient()
    result = client.summarize("Це тестовий текст для перевірки роботи OpenAI клієнта.")
    print("AI summary:", result)


def main():
    print("🔧 DEBUG mode active")
    print("🔑 OPENAI_API_KEY:", settings.OPENAI_API_KEY[:8] + "...")

    test_confluence()
    test_openai()

    print("\n🎉 Усі тести виконано!")


if __name__ == "__main__":
    main()