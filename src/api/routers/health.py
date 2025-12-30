from fastapi import APIRouter
from src.core.ai.health import check_ai_health
from src.core.config.ai_settings import settings

router = APIRouter()


@router.get("/health")
def health_check():
    """Basic health check endpoint."""
    return {"status": "ok"}


@router.get("/health/ai")
async def ai_health_check():
    """
    AI providers health check endpoint.
    
    Checks the health of all configured AI providers (OpenAI, Gemini)
    by making lightweight API calls to verify connectivity and authentication.
    
    Returns:
        dict: Health report with status for each provider
        
    Example Response:
        {
            "all_ok": true,
            "providers": {
                "openai": {
                    "ok": true,
                    "error": null,
                    "details": {
                        "model": "gpt-4o-mini",
                        "total_tokens": 5
                    }
                },
                "gemini": {
                    "ok": true,
                    "error": null,
                    "details": {
                        "model": "gemini-2.0-flash-exp",
                        "tokens_for_ping": 4
                    }
                }
            },
            "healthy_providers": ["openai", "gemini"],
            "unhealthy_providers": []
        }
    """
    report = await check_ai_health(settings)
    
    return {
        "all_ok": report.all_ok,
        "providers": {
            name: {
                "ok": ph.ok,
                "error": ph.error,
                "details": ph.details,
            }
            for name, ph in report.providers.items()
        },
        "healthy_providers": report.healthy_providers,
        "unhealthy_providers": report.unhealthy_providers,
    }
