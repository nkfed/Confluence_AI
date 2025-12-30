"""AI provider interface package initialization."""

from src.core.ai.interface import AIResponse, AIProvider, AIProviderType
from src.core.ai.openai_client import OpenAIClient
from src.core.ai.gemini_client import GeminiClient
from src.core.ai.router import AIProviderRouter
from src.core.ai.rate_limit import RateLimitConfig, SimpleRateLimiter
from src.core.ai.costs import CostConfig, CostEstimate, CostCalculator
from src.core.ai.health import (
    ProviderHealth,
    AIHealthReport,
    check_ai_health,
    check_provider_openai,
    check_provider_gemini,
)

__all__ = [
    "AIResponse",
    "AIProvider",
    "AIProviderType",
    "OpenAIClient",
    "GeminiClient",
    "AIProviderRouter",
    "RateLimitConfig",
    "SimpleRateLimiter",
    "CostConfig",
    "CostEstimate",
    "CostCalculator",
    "ProviderHealth",
    "AIHealthReport",
    "check_ai_health",
    "check_provider_openai",
    "check_provider_gemini",
]
