"""
Custom exceptions for AI Provider operations.

Provides a hierarchy of exceptions for better error handling and fallback logic.
"""


class AIProviderError(Exception):
    """
    Base exception for all AI provider-related errors.
    
    This is the root exception that all other AI provider exceptions inherit from.
    Use this for catching any AI provider error in generic error handlers.
    
    Example:
        >>> try:
        ...     result = await router.generate("prompt")
        ... except AIProviderError as e:
        ...     logger.error(f"AI provider error: {e}")
        ...     # Handle any AI provider error
    """
    pass


class RateLimitError(AIProviderError):
    """
    Exception raised when API rate limit is exceeded.
    
    This occurs when too many requests are made to the AI provider
    within a given time period. The request should be retried after
    a delay.
    
    Example:
        >>> try:
        ...     result = await client.generate("prompt")
        ... except RateLimitError:
        ...     logger.warning("Rate limit exceeded, waiting...")
        ...     await asyncio.sleep(60)
        ...     result = await client.generate("prompt")
    """
    pass


class ProviderUnavailableError(AIProviderError):
    """
    Exception raised when AI provider is unavailable or not configured.
    
    This can occur when:
    - Provider is not registered in the router
    - API key is missing or invalid
    - Provider service is down
    - Network connectivity issues
    
    Example:
        >>> try:
        ...     client = router.get("unknown-provider")
        ... except ProviderUnavailableError as e:
        ...     logger.error(f"Provider unavailable: {e}")
        ...     # Use alternative provider or fail gracefully
    """
    pass


class FallbackFailedError(AIProviderError):
    """
    Exception raised when both primary and fallback providers fail.
    
    This is a critical error indicating that all configured providers
    have failed to process the request. This typically requires
    immediate attention.
    
    The exception message contains details about both failures.
    
    Example:
        >>> try:
        ...     result = await router.generate("prompt")
        ... except FallbackFailedError as e:
        ...     logger.critical(f"All providers failed: {e}")
        ...     # Send alert, return error to user
    """
    pass


__all__ = [
    "AIProviderError",
    "RateLimitError",
    "ProviderUnavailableError",
    "FallbackFailedError",
]
