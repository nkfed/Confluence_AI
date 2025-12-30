"""
AI Provider Router.

This module provides a central router for managing and selecting AI providers,
with support for fallback mechanisms and lazy loading.
"""

from typing import Dict, Optional, Any
from src.core.ai.interface import AIProvider, AIResponse
from src.core.ai.openai_client import OpenAIClient
from src.core.ai.gemini_client import GeminiClient
from src.core.ai.errors import ProviderUnavailableError, FallbackFailedError
from src.core.logging.logger import get_logger

logger = get_logger(__name__)


class AIProviderRouter:
    """
    Central router for AI provider selection and management.
    
    This router handles provider selection, lazy loading, and fallback mechanisms
    for AI text generation across multiple providers (OpenAI, Gemini, etc.).
    
    Features:
    - Lazy loading of providers (only initialized when needed)
    - Default provider configuration
    - Fallback to alternative provider on errors
    - Centralized provider management
    - Convenient generate() shortcut method
    
    Example:
        >>> router = AIProviderRouter(default_provider="openai", fallback_provider="gemini")
        >>> response = await router.generate("Your prompt")
        >>> # Will use OpenAI by default, fallback to Gemini on errors
        
        >>> response = await router.generate("Your prompt", provider="gemini")
        >>> # Explicitly use Gemini
    """
    
    def __init__(
        self,
        default_provider: str = "openai",
        fallback_provider: Optional[str] = None,
        providers: Optional[Dict[str, AIProvider]] = None,
        auto_register: bool = True,
    ):
        """
        Initialize AI Provider Router.
        
        Args:
            default_provider: Name of the default provider to use ('openai' or 'gemini')
            fallback_provider: Name of fallback provider if default fails (optional)
            providers: Pre-initialized providers dict (optional, for testing)
            auto_register: Whether to automatically register OpenAI and Gemini (default: True)
        """
        self._default = default_provider
        self._fallback = fallback_provider
        self._providers: Dict[str, AIProvider] = providers if providers is not None else {}
        
        logger.info(
            f"AI Provider Router initialized: default={default_provider}, "
            f"fallback={fallback_provider}"
        )
        
        # Lazy registration of providers
        if auto_register:
            self._lazy_register_providers()
    
    def _lazy_register_providers(self):
        """
        Lazily register OpenAI and Gemini providers.
        
        Only initializes providers if they can be configured (API keys available).
        Silently ignores providers that can't be initialized.
        """
        # Try to register OpenAI
        if "openai" not in self._providers:
            try:
                self._providers["openai"] = OpenAIClient()
                logger.info("OpenAI provider registered successfully")
            except ValueError as e:
                logger.warning(f"Could not register OpenAI provider: {e}")
            except Exception as e:
                logger.warning(f"Unexpected error registering OpenAI: {e}")
        
        # Try to register Gemini
        if "gemini" not in self._providers:
            try:
                self._providers["gemini"] = GeminiClient()
                logger.info("Gemini provider registered successfully")
            except ValueError as e:
                logger.warning(f"Could not register Gemini provider: {e}")
            except Exception as e:
                logger.warning(f"Unexpected error registering Gemini: {e}")
    
    def register(self, name: str, provider: AIProvider) -> None:
        """
        Manually register a provider.
        
        Args:
            name: Provider name (e.g., 'openai', 'gemini', 'custom')
            provider: AIProvider implementation instance
        """
        self._providers[name] = provider
        logger.info(f"Manually registered provider: {name}")
    
    def get(self, name: Optional[str] = None) -> AIProvider:
        """
        Get a provider by name.
        
        Args:
            name: Provider name (defaults to configured default provider)
            
        Returns:
            AIProvider: The requested provider instance
            
        Raises:
            ValueError: If provider is not registered or configured
        """
        provider_name = name or self._default
        
        if provider_name not in self._providers:
            available = ", ".join(self._providers.keys())
            raise ValueError(
                f"AI provider '{provider_name}' is not configured. "
                f"Available providers: {available or 'none'}"
            )
        
        logger.debug(f"Getting provider: {provider_name}")
        return self._providers[provider_name]
    
    async def generate(
        self,
        prompt: str,
        provider: Optional[str] = None,
        **kwargs: Any
    ) -> AIResponse:
        """
        Generate text using specified or default provider with fallback support.
        
        This is a convenience method that automatically handles provider selection
        and fallback to alternative provider on errors.
        
        Args:
            prompt: Text prompt for generation
            provider: Provider name (optional, uses default if not specified)
            **kwargs: Additional parameters passed to provider's generate method
                     (temperature, max_tokens, etc.)
        
        Returns:
            AIResponse: Standardized response with generated text
            
        Raises:
            ProviderUnavailableError: If provider is not configured or unavailable
            FallbackFailedError: If both primary and fallback providers fail
        """
        provider_name = provider or self._default
        
        # 1. Get primary provider
        try:
            logger.info(f"Generating with provider: {provider_name}")
            client = self.get(provider_name)
        except ValueError as exc:
            raise ProviderUnavailableError(str(exc)) from exc
        
        # 2. Primary attempt
        try:
            response = await client.generate(prompt, **kwargs)
            logger.info(f"Successfully generated with {provider_name}")
            return response
            
        except Exception as primary_exc:
            logger.warning(f"Provider {provider_name} failed: {primary_exc}")
            
            # If no fallback configured or fallback is same as primary -> raise error
            if not self._fallback or self._fallback == provider_name:
                raise ProviderUnavailableError(
                    f"Primary provider '{provider_name}' failed: {primary_exc}"
                ) from primary_exc
            
            # 3. Fallback attempt
            logger.info(f"Attempting fallback to: {self._fallback}")
            try:
                fallback_client = self.get(self._fallback)
                response = await fallback_client.generate(prompt, **kwargs)
                logger.info(f"Successfully generated with fallback {self._fallback}")
                return response
                
            except Exception as fallback_exc:
                logger.error(f"Fallback provider {self._fallback} also failed: {fallback_exc}")
                raise FallbackFailedError(
                    f"Primary provider '{provider_name}' failed: {primary_exc}; "
                    f"Fallback provider '{self._fallback}' failed: {fallback_exc}"
                ) from fallback_exc
    
    async def count_tokens(
        self,
        text: str,
        provider: Optional[str] = None,
        **kwargs: Any
    ) -> int:
        """
        Count tokens using specified or default provider.
        
        Args:
            text: Text to count tokens for
            provider: Provider name (optional, uses default if not specified)
            **kwargs: Additional parameters
            
        Returns:
            int: Number of tokens
            
        Raises:
            ValueError: If provider is not configured
            NotImplementedError: If provider doesn't support token counting
        """
        client = self.get(provider)
        return await client.count_tokens(text, **kwargs)
    
    @property
    def providers(self) -> Dict[str, str]:
        """
        Get dictionary of registered provider names and their types.
        
        Returns:
            Dict[str, str]: Mapping of provider name to provider class name
        """
        return {
            name: type(provider).__name__
            for name, provider in self._providers.items()
        }
    
    @property
    def default_provider(self) -> str:
        """Get the default provider name."""
        return self._default
    
    @property
    def fallback_provider(self) -> Optional[str]:
        """Get the fallback provider name (if configured)."""
        return self._fallback
    
    def has_provider(self, name: str) -> bool:
        """
        Check if a provider is registered.
        
        Args:
            name: Provider name
            
        Returns:
            bool: True if provider is registered
        """
        return name in self._providers
    
    async def explain(self, settings: Optional[Any] = None) -> dict:
        """
        Return detailed diagnostics of current AI routing state.
        
        Provides comprehensive information about routing configuration,
        registered providers, models, API keys, and health status.
        
        Useful for:
        - Debugging routing issues
        - Pre-deployment checks
        - Health dashboards
        - CI/CD validation
        - Configuration verification
        
        Args:
            settings: AI settings (uses default if not provided)
            
        Returns:
            dict: Detailed routing diagnostics including:
                - routing_mode: Active routing mode (A/B/C/D)
                - default_provider: Primary provider name
                - fallback_provider: Fallback provider name
                - registered_providers: List of available providers
                - models: Model configuration for each provider
                - api_keys: API key availability (boolean)
                - health: Health status for each provider
                - all_providers_ok: Overall health status
                
        Example:
            >>> router = AIProviderRouter()
            >>> report = await router.explain()
            >>> print(f"Mode: {report['routing_mode']}")
            >>> print(f"Primary: {report['default_provider']}")
            >>> print(f"All OK: {report['all_providers_ok']}")
        """
        from src.core.config.ai_settings import AISettings
        from src.core.ai.health import check_ai_health
        
        settings = settings or AISettings()
        
        # Perform health check
        health_report = await check_ai_health(settings)
        
        return {
            "routing_mode": settings.AI_ROUTING_MODE,
            "default_provider": self._default,
            "fallback_provider": self._fallback,
            "registered_providers": sorted(self._providers.keys()),
            "models": {
                "openai": settings.OPENAI_MODEL,
                "gemini": settings.GEMINI_MODEL,
            },
            "api_keys": {
                "openai": bool(settings.OPENAI_API_KEY),
                "gemini": bool(settings.GEMINI_API_KEY),
            },
            "health": {
                name: {
                    "ok": ph.ok,
                    "error": ph.error,
                    "details": ph.details,
                }
                for name, ph in health_report.providers.items()
            },
            "all_providers_ok": health_report.all_ok,
        }


__all__ = ["AIProviderRouter"]
