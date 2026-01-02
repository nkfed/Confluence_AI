"""
AI Provider Health Check Module.

Provides health check functionality for AI providers (OpenAI, Gemini)
to verify connectivity and configuration before running agents.
"""

from dataclasses import dataclass
from typing import Literal, Optional, Dict, Any
from src.core.ai.openai_client import OpenAIClient
from src.core.ai.gemini_client import GeminiClient
from src.core.config.ai_settings import AISettings
from src.core.logging.logger import get_logger

logger = get_logger(__name__)

ProviderName = Literal["openai", "gemini"]


@dataclass
class ProviderHealth:
    """
    Health status for a single AI provider.
    
    Attributes:
        name: Provider name ('openai' or 'gemini')
        ok: Whether provider is healthy and operational
        error: Error message if provider check failed
        details: Additional provider-specific details
    """
    name: ProviderName
    ok: bool
    error: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


@dataclass
class AIHealthReport:
    """
    Complete health report for all AI providers.
    
    Attributes:
        providers: Dictionary mapping provider name to health status
    """
    providers: Dict[ProviderName, ProviderHealth]
    
    @property
    def all_ok(self) -> bool:
        """Check if all providers are healthy."""
        return all(p.ok for p in self.providers.values())
    
    @property
    def healthy_providers(self) -> list[ProviderName]:
        """Get list of healthy provider names."""
        return [name for name, health in self.providers.items() if health.ok]
    
    @property
    def unhealthy_providers(self) -> list[ProviderName]:
        """Get list of unhealthy provider names."""
        return [name for name, health in self.providers.items() if not health.ok]


async def check_provider_openai(settings: AISettings) -> ProviderHealth:
    """
    Check OpenAI provider health.
    
    Performs a lightweight health check by making a minimal API request
    to verify connectivity and authentication.
    
    Args:
        settings: AI settings configuration
        
    Returns:
        ProviderHealth: Health status for OpenAI provider
    """
    logger.debug("Checking OpenAI provider health")
    
    if not settings.OPENAI_API_KEY:
        logger.warning("OpenAI health check failed: API key not set")
        return ProviderHealth(
            name="openai",
            ok=False,
            error="OPENAI_API_KEY not set"
        )
    
    try:
        client = OpenAIClient(
            api_key=settings.OPENAI_API_KEY,
            model_default=settings.OPENAI_MODEL,
        )
        
        # Lightweight ping: minimal request to verify connectivity
        resp = await client.generate("ping", max_tokens=1)
        
        logger.info(f"OpenAI health check passed (model={resp.model}, tokens={resp.total_tokens})")
        
        return ProviderHealth(
            name="openai",
            ok=True,
            details={
                "model": resp.model,
                "total_tokens": resp.total_tokens,
                "provider": resp.provider,
            },
        )
    except Exception as exc:
        logger.error(f"OpenAI health check failed: {exc}")
        return ProviderHealth(
            name="openai",
            ok=False,
            error=str(exc)
        )


async def check_provider_gemini(settings: AISettings) -> ProviderHealth:
    """
    Check Gemini provider health.
    
    Performs a lightweight health check using token counting API
    to verify connectivity and authentication.
    
    Args:
        settings: AI settings configuration
        
    Returns:
        ProviderHealth: Health status for Gemini provider
    """
    logger.debug("Checking Gemini provider health")
    
    if not settings.GEMINI_API_KEY:
        logger.warning("Gemini health check failed: API key not set")
        return ProviderHealth(
            name="gemini",
            ok=False,
            error="GEMINI_API_KEY not set"
        )
    
    try:
        async with GeminiClient(
            api_key=settings.GEMINI_API_KEY,
            model_default=settings.GEMINI_MODEL,
        ) as client:
            # Lightweight check: token counting is fast and cheap
            count = await client.count_tokens("ping")
        
        logger.info(f"Gemini health check passed (model={settings.GEMINI_MODEL}, tokens={count})")
        
        return ProviderHealth(
            name="gemini",
            ok=True,
            details={
                "model": settings.GEMINI_MODEL,
                "tokens_for_ping": count,
            },
        )
    except Exception as exc:
        logger.error(f"Gemini health check failed: {exc}")
        return ProviderHealth(
            name="gemini",
            ok=False,
            error=str(exc)
        )


async def check_ai_health(settings: Optional[AISettings] = None) -> AIHealthReport:
    """
    Check health of all configured AI providers.
    
    Performs health checks on OpenAI and Gemini providers in parallel
    to quickly determine which providers are available and healthy.
    
    Args:
        settings: AI settings (uses default if not provided)
        
    Returns:
        AIHealthReport: Complete health report for all providers
        
    Example:
        >>> from src.core.ai.health import check_ai_health
        >>> report = await check_ai_health()
        >>> if report.all_ok:
        ...     print("All providers healthy!")
        >>> else:
        ...     print(f"Unhealthy: {report.unhealthy_providers}")
    """
    settings = settings or AISettings()
    
    logger.info("Starting AI health check")
    
    providers: Dict[ProviderName, ProviderHealth] = {}
    
    # Check OpenAI
    providers["openai"] = await check_provider_openai(settings)
    
    # Check Gemini
    providers["gemini"] = await check_provider_gemini(settings)
    
    report = AIHealthReport(providers=providers)
    
    if report.all_ok:
        logger.info("✅ All AI providers healthy")
    else:
        logger.warning(
            f"⚠️ Some AI providers unhealthy: {report.unhealthy_providers}"
        )
    
    return report


__all__ = [
    "ProviderHealth",
    "AIHealthReport",
    "check_provider_openai",
    "check_provider_gemini",
    "check_ai_health",
]
