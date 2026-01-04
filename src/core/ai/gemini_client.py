"""
Google Gemini Provider Implementation.

This module provides a Gemini client that implements the AIProvider interface,
using Google's Generative AI REST API for text generation and token counting.
"""

import asyncio
import os
import random
import time
from typing import Any, Optional
import httpx
from src.core.ai.interface import AIProvider, AIResponse
from src.core.ai.rate_limit import SimpleRateLimiter
from src.core.ai.optimization_patch_v2 import get_optimization_patch_v2
from src.core.logging.logger import get_logger
from src.core.logging.timing import log_timing

logger = get_logger(__name__)
router_logger = get_logger("ai_router")


class GeminiClient:
    """
    Google Gemini provider implementation conforming to AIProvider protocol.
    
    This client uses Google's Generative AI REST API (v1beta) and provides
    a standardized interface for text generation and token counting.
    
    Attributes:
        name: Provider identifier ('gemini')
        model_default: Default model to use for generation
        base_url: Base URL for Google Generative AI API
    """
    
    name = "gemini"
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model_default: str = "gemini-2.0-flash-exp",
        timeout: float = 30.0,
        rate_limiter: Optional[SimpleRateLimiter] = None,
    ):
        """
        Initialize Gemini client.
        
        Args:
            api_key: Google API key (defaults to GOOGLE_API_KEY or GEMINI_API_KEY env var)
            model_default: Default model for generation (e.g., 'gemini-2.0-flash-exp', 'gemini-1.5-pro')
            timeout: HTTP request timeout in seconds
            rate_limiter: Optional rate limiter to prevent 429 errors
            
        Raises:
            ValueError: If API key is not provided and env vars are not set
        """
        # Try multiple environment variable names
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Gemini API key is not set. Please provide api_key or set "
                "GEMINI_API_KEY or GOOGLE_API_KEY environment variable."
            )
        
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
        self.model_default = model_default
        self._client = httpx.AsyncClient(timeout=timeout)
        self._rate_limiter = rate_limiter
        
        logger.info(f"Gemini client initialized with default model: {model_default}")
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self._client.aclose()
    
    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()
    
    @log_timing
    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_retries: int = 2,
        **kwargs: Any
    ) -> AIResponse:
        """
        Generate text completion using Gemini API.
        
        Args:
            prompt: Text prompt for generation
            model: Model to use (overrides default)
                   Examples: 'gemini-2.0-flash-exp', 'gemini-1.5-pro', 'gemini-1.5-flash'
            max_retries: Number of retry attempts for rate limits
            **kwargs: Additional generation parameters
                     (temperature, maxOutputTokens, topK, topP, etc.)
        
        Returns:
            AIResponse: Standardized response with text and metadata
            
        Raises:
            RuntimeError: If API request fails after all retries
        """
        model_name = model or self.model_default
        # Ensure model name has 'models/' prefix if not already present
        if not model_name.startswith("models/"):
            model_name = f"models/{model_name}"
        
        url = f"{self.base_url}/{model_name}:generateContent"
        delay = 1  # Initial delay in seconds
        
        # Build payload
        payload = {
            "contents": [
                {
                    "parts": [{"text": prompt}]
                }
            ]
        }
        
        # Add generation config if kwargs provided
        if kwargs:
            generation_config = {}
            # Map common parameters
            if "temperature" in kwargs:
                generation_config["temperature"] = kwargs["temperature"]
            if "max_tokens" in kwargs:
                generation_config["maxOutputTokens"] = kwargs["max_tokens"]
            if "top_p" in kwargs:
                generation_config["topP"] = kwargs["top_p"]
            if "top_k" in kwargs:
                generation_config["topK"] = kwargs["top_k"]
            
            if generation_config:
                payload["generationConfig"] = generation_config
        
        params = {"key": self.api_key}
        
        # Initialize patch for metrics
        patch = get_optimization_patch_v2()
        call_start_time = time.time()
        
        # Pre-flight rate control: check if we should wait before calling
        await patch.preflight_cooldown()
        
        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"[Gemini] Attempt {attempt}/{max_retries} with model {model_name}")
                
                # Apply rate limiting before API call
                if self._rate_limiter:
                    self._rate_limiter.before_call()
                
                # Call Gemini API
                response = await self._client.post(url, params=params, json=payload)
                response.raise_for_status()
                data = response.json()
                
                # Extract text from response
                candidates = data.get("candidates", [])
                text_parts = []
                
                if candidates:
                    content = candidates[0].get("content", {})
                    parts = content.get("parts", [])
                    for part in parts:
                        if "text" in part:
                            text_parts.append(part["text"])
                
                text = "\n".join(text_parts).strip() if text_parts else ""
                
                # Extract token usage
                usage = data.get("usageMetadata", {}) or {}
                prompt_tokens = usage.get("promptTokenCount")
                completion_tokens = usage.get("candidatesTokenCount")
                total_tokens = usage.get("totalTokenCount")
                
                logger.info(
                    f"[Gemini] Success! Tokens: {total_tokens} "
                    f"(prompt: {prompt_tokens}, completion: {completion_tokens})"
                )
                
                # Record call metrics to patch
                duration_ms = (time.time() - call_start_time) * 1000
                await patch.record_call(
                    provider="gemini",
                    success=True,
                    tokens=total_tokens,
                    duration_ms=duration_ms,
                    cooldown_reason="normal",
                    cooldown_ms=0
                )
                
                # Convert to standardized response
                return AIResponse(
                    text=text,
                    raw=data,
                    provider=self.name,
                    model=model_name,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens
                )
                
            except httpx.HTTPStatusError as e:
                error_text = str(e)
                status_code = e.response.status_code
                
                # Handle rate limit errors (429) and quota errors (503)
                if status_code in (429, 503):
                    logger.warning(f"[Gemini] Rate limit/quota hit on attempt {attempt}: {e}")
                    router_logger.info(
                        f"[RETRY] Provider=gemini, attempt={attempt}, error={e}, switching=False"
                    )
                    
                    # Record 429 error in patch
                    patch.record_429()
                    
                    if attempt == max_retries:
                        logger.error("[Gemini] Max retries reached, giving up")
                        
                        # Record failed call to patch
                        duration_ms = (time.time() - call_start_time) * 1000
                        await patch.record_call(
                            provider="gemini",
                            success=False,
                            tokens=0,
                            duration_ms=duration_ms,
                            fallback_reason="429_max_retries",
                            cooldown_reason=None,
                            cooldown_ms=0
                        )
                        
                        raise RuntimeError(
                            f"Gemini rate limit error after {max_retries} attempts: {e}"
                        )
                    
                    # Adaptive cooldown: escalating wait based on consecutive 429s
                    reason, wait_ms = await patch.adaptive_cooldown()
                    logger.info(f"[PATCH v2] Adaptive cooldown: {reason} - waiting {wait_ms}ms")
                    delay *= 2  # Exponential backoff
                    continue
                
                # Other HTTP errors - raise immediately
                logger.error(f"[Gemini] HTTP error {status_code}: {e}")
                
                # Record error to patch
                duration_ms = (time.time() - call_start_time) * 1000
                await patch.record_call(
                    provider="gemini",
                    success=False,
                    tokens=0,
                    duration_ms=duration_ms,
                    fallback_reason=f"http_{status_code}",
                    cooldown_reason=None,
                    cooldown_ms=0
                )
                
                try:
                    error_body = e.response.json()
                    logger.error(f"[Gemini] Error details: {error_body}")
                except Exception:
                    pass
                raise RuntimeError(f"Gemini API HTTP error: {e}")
                
            except Exception as e:
                logger.error(f"[Gemini] Unexpected error: {e}")
                
                # Record error to patch
                duration_ms = (time.time() - call_start_time) * 1000
                await patch.record_call(
                    provider="gemini",
                    success=False,
                    tokens=0,
                    duration_ms=duration_ms,
                    fallback_reason="unexpected_error",
                    cooldown_reason=None,
                    cooldown_ms=0
                )
                
                raise RuntimeError(f"Gemini API error: {e}")
    
    async def count_tokens(
        self,
        text: str,
        model: Optional[str] = None,
        **kwargs: Any
    ) -> int:
        """
        Count tokens in text using Gemini API.
        
        Args:
            text: Text to tokenize
            model: Model name for tokenizer (defaults to model_default)
            **kwargs: Additional parameters
            
        Returns:
            int: Number of tokens
            
        Raises:
            RuntimeError: If API request fails
        """
        model_name = model or self.model_default
        # Ensure model name has 'models/' prefix
        if not model_name.startswith("models/"):
            model_name = f"models/{model_name}"
        
        url = f"{self.base_url}/{model_name}:countTokens"
        
        payload = {
            "contents": [
                {
                    "parts": [{"text": text}]
                }
            ]
        }
        
        params = {"key": self.api_key}
        
        try:
            logger.debug(f"[Gemini] Counting tokens for text length: {len(text)}")
            
            # Apply rate limiting before API call
            if self._rate_limiter:
                self._rate_limiter.before_call()
            
            response = await self._client.post(url, params=params, json=payload)
            response.raise_for_status()
            data = response.json()
            
            total_tokens = int(data.get("totalTokens", 0))
            logger.debug(f"[Gemini] Token count: {total_tokens}")
            
            return total_tokens
            
        except httpx.HTTPStatusError as e:
            logger.error(f"[Gemini] Token counting HTTP error: {e}")
            raise RuntimeError(f"Gemini token counting error: {e}")
        except Exception as e:
            logger.error(f"[Gemini] Token counting error: {e}")
            raise RuntimeError(f"Gemini token counting error: {e}")
    
    async def embed(self, text: str, **kwargs: Any) -> list[float]:
        """
        Generate embeddings for text using Gemini API.
        
        Args:
            text: Text to embed
            **kwargs: Additional parameters
            
        Returns:
            list[float]: Vector representation of text
            
        Raises:
            NotImplementedError: Embeddings not yet implemented
        """
        # TODO: Implement embeddings using Gemini embeddings API
        # model = kwargs.get("model", "models/text-embedding-004")
        # url = f"{self.base_url}/{model}:embedContent"
        # payload = {"content": {"parts": [{"text": text}]}}
        # ...
        raise NotImplementedError("Embeddings not implemented for Gemini yet")


__all__ = ["GeminiClient"]
