from core.config.ai_settings import AISettings
from core.ai.health import check_ai_health
from core.ai.router import router
from core.ai.costs import CostCalculator
from core.ai.logging_utils import log_ai_call
from core.agents.summary_agent import SummaryAgent
from core.agents.tagging_agent import TaggingAgent
from core.ai.errors import AIProviderError
import asyncio


async def run_smoke_test():
    print("🔍 Smoke Test Started\n")

    # 1. AISettings
    try:
        settings = AISettings()
        print("✅ AISettings loaded")
        print(f"   Routing Mode: {settings.AI_ROUTING_MODE}")
        print(f"   OpenAI Model: {settings.OPENAI_MODEL}")
        print(f"   Gemini Model: {settings.GEMINI_MODEL}")
    except Exception as e:
        print(f"❌ Failed to load AISettings: {e}")
        return

    # 2. Health Check
    try:
        health = await check_ai_health(settings)
        for name, status in health.providers.items():
            print(f"✅ {name} health: {'OK' if status.ok else 'FAIL'}")
        print(f"   All providers OK: {health.all_ok}")
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return

    # 3. Cost Tracking
    try:
        calc = CostCalculator()
        cost = calc.estimate("openai", 1000, 500)
        print(f"✅ Cost Tracking OK: ${cost.total_usd:.4f} for 1000p + 500c")
    except Exception as e:
        print(f"❌ Cost tracking failed: {e}")

    # 4. Router
    try:
        resp = await router.generate("Test prompt for router")
        print(f"✅ Router OK: response = {resp.text[:50]}...")
    except AIProviderError as e:
        print(f"⚠️ Router fallback triggered: {e}")
    except Exception as e:
        print(f"❌ Router failed: {e}")

    # 5. SummaryAgent
    try:
        summary = await SummaryAgent().run("This is a test summary input.")
        print(f"✅ SummaryAgent OK: {summary[:50]}...")
    except Exception as e:
        print(f"❌ SummaryAgent failed: {e}")

    # 6. TaggingAgent
    try:
        tags = await TaggingAgent().run("This is a test tagging input about AI and cloud.")
        print(f"✅ TaggingAgent OK: {tags}")
    except Exception as e:
        print(f"❌ TaggingAgent failed: {e}")

    print("\n✅ Smoke Test Completed")


if __name__ == "__main__":
    asyncio.run(run_smoke_test())