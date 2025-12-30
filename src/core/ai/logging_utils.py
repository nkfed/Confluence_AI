"""
Unified Logging Layer for AI Provider Calls.

Provides centralized logging for all AI API calls with automatic tracking of:
- Provider and model information
- Execution time
- Token usage
- Cost estimates
- Errors and exceptions
"""

import time
from typing import Any, Callable, Awaitable, Optional
from src.core.logging.logger import get_logger
from src.core.ai.costs import CostCalculator

logger = get_logger(__name__)


async def log_ai_call(
    provider_name: str,
    model: Optional[str],
    operation: str,
    coro: Callable[[], Awaitable[Any]],
) -> Any:
    """
    Universal logging wrapper for AI provider calls.
    
    Automatically logs:
    - Provider and model information
    - Operation type (summary, tagging, etc.)
    - Execution time
    - Token usage (prompt, completion, total)
    - Cost estimate in USD
    - Errors and exceptions
    
    Args:
        provider_name: Name of AI provider ('openai', 'gemini')
        model: Model name (e.g., 'gpt-4o-mini', 'gemini-2.0-flash-exp')
        operation: Operation type ('summary', 'tagging', 'custom', etc.)
        coro: Async callable that performs the AI operation
        
    Returns:
        Result from the AI operation
        
    Raises:
        Exception: Re-raises any exception from the AI operation after logging
        
    Example:
        >>> result = await log_ai_call(
        ...     provider_name="openai",
        ...     model="gpt-4o-mini",
        ...     operation="summary",
        ...     coro=lambda: client.generate("Summarize this text")
        ... )
        INFO AI call succeeded provider=openai model=gpt-4o-mini operation=summary
             duration_sec=0.42 prompt_tokens=12 completion_tokens=48 total_tokens=60
             cost_usd=0.00009
    """
    start = time.time()
    calculator = CostCalculator()
    
    try:
        # Execute AI operation
        result = await coro()
        duration = time.time() - start
        
        # Extract token information
        tokens_info = {}
        cost = None
        
        if hasattr(result, "prompt_tokens") and hasattr(result, "completion_tokens"):
            # Result has token information (AIResponse)
            tokens_info = {
                "prompt_tokens": result.prompt_tokens,
                "completion_tokens": result.completion_tokens,
                "total_tokens": result.total_tokens,
            }
            
            # Calculate cost estimate
            if result.prompt_tokens and result.completion_tokens:
                cost = calculator.estimate(
                    provider=provider_name,
                    prompt_tokens=result.prompt_tokens,
                    completion_tokens=result.completion_tokens,
                )
        
        # Log success
        logger.info(
            "AI call succeeded",
            extra={
                "provider": provider_name,
                "model": model,
                "operation": operation,
                "duration_sec": round(duration, 4),
                **tokens_info,
                "cost_usd": cost.total_usd if cost else None,
            },
        )
        
        return result
    
    except Exception as exc:
        # Calculate duration even on failure
        duration = time.time() - start
        
        # Log failure
        logger.error(
            "AI call failed",
            extra={
                "provider": provider_name,
                "model": model,
                "operation": operation,
                "duration_sec": round(duration, 4),
                "error": str(exc),
                "error_type": exc.__class__.__name__,
            },
        )
        
        # Re-raise exception
        raise


__all__ = ["log_ai_call"]
