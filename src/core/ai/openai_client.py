"""
OpenAI Provider Implementation.

This module provides an OpenAI client that implements the AIProvider interface,
allowing seamless integration with the multi-AI architecture.
"""

import asyncio
import os
from typing import Any, Optional
from openai import AsyncOpenAI
from src.core.ai.interface import AIProvider, AIResponse
from src.core.logging.logger import get_logger
from src.core.logging.timing import log_timing

logger = get_logger(__name__)


class OpenAIClient:
    """
    OpenAI provider implementation conforming to AIProvider protocol.
    
    This client wraps the OpenAI AsyncOpenAI SDK and provides a standardized
    interface for text generation, token counting, and embeddings.
    
    Attributes:
        name: Provider identifier ('openai')
        model_default: Default model to use for generation
        client: AsyncOpenAI SDK client instance
    """
    
    name = "openai"
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model_default: str = "gpt-4o-mini"
    ):
        """
        Initialize OpenAI client.
        
        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            model_default: Default model for generation
            
        Raises:
            ValueError: If API key is not provided and OPENAI_API_KEY env var is not set
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is not set. Please provide api_key or set environment variable.")
        
        self.client = AsyncOpenAI(api_key=self.api_key)
        self.model_default = model_default
        logger.info(f"OpenAI client initialized with default model: {model_default}")
    
    @log_timing
    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_retries: int = 5,
        **kwargs: Any
    ) -> AIResponse:
        """
        Generate text completion using OpenAI API.
        
        Args:
            prompt: Text prompt for generation
            model: Model to use (overrides default)
            max_retries: Number of retry attempts for rate limits
            **kwargs: Additional parameters passed to OpenAI API
                     (temperature, max_tokens, etc.)
        
        Returns:
            AIResponse: Standardized response with text and metadata
            
        Raises:
            RuntimeError: If API request fails after all retries
        """
        model_name = model or self.model_default
        delay = 1  # Initial delay in seconds
        
        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"[OpenAI] Attempt {attempt}/{max_retries} with model {model_name}")
                
                # Call OpenAI API
                response = await self.client.chat.completions.create(
                    model=model_name,
                    messages=[{"role": "user", "content": prompt}],
                    **kwargs
                )
                
                # Extract text from response
                text = response.choices[0].message.content or ""
                
                # Extract token usage
                usage = response.usage
                prompt_tokens = usage.prompt_tokens if usage else None
                completion_tokens = usage.completion_tokens if usage else None
                total_tokens = usage.total_tokens if usage else None
                
                logger.info(
                    f"[OpenAI] Success! Tokens: {total_tokens} "
                    f"(prompt: {prompt_tokens}, completion: {completion_tokens})"
                )
                
                # Convert to standardized response
                return AIResponse(
                    text=text,
                    raw=response.model_dump() if hasattr(response, 'model_dump') else None,
                    provider=self.name,
                    model=model_name,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens
                )
                
            except Exception as e:
                error_text = str(e)
                
                # Handle rate limit errors (429)
                if "rate_limit" in error_text.lower() or "429" in error_text:
                    logger.warning(f"[OpenAI] Rate limit hit on attempt {attempt}: {e}")
                    
                    if attempt == max_retries:
                        logger.error("[OpenAI] Max retries reached, giving up")
                        raise RuntimeError(
                            f"OpenAI rate limit error after {max_retries} attempts: {e}"
                        )
                    
                    logger.info(f"[OpenAI] Waiting {delay}s before retry...")
                    await asyncio.sleep(delay)
                    delay *= 2  # Exponential backoff
                    continue
                
                # Other errors - raise immediately
                logger.error(f"[OpenAI] Unexpected error: {e}")
                raise RuntimeError(f"OpenAI API error: {e}")
    
    async def embed(self, text: str, **kwargs: Any) -> list[float]:
        """
        Generate embeddings for text using OpenAI API.
        
        Args:
            text: Text to embed
            **kwargs: Additional parameters (model, etc.)
            
        Returns:
            list[float]: Vector representation of text
            
        Raises:
            NotImplementedError: Embeddings not yet implemented
        """
        # TODO: Implement embeddings using OpenAI embeddings API
        # model = kwargs.get("model", "text-embedding-3-small")
        # response = await self.client.embeddings.create(
        #     model=model,
        #     input=text
        # )
        # return response.data[0].embedding
        raise NotImplementedError("Embeddings not implemented for OpenAI yet")
    
    async def count_tokens(self, text: str, model: Optional[str] = None, **kwargs: Any) -> int:
        """
        Count tokens in text using tiktoken.
        
        Args:
            text: Text to tokenize
            model: Model name for tokenizer (defaults to model_default)
            **kwargs: Additional parameters
            
        Returns:
            int: Number of tokens
            
        Raises:
            NotImplementedError: Token counting not yet implemented
        """
        # TODO: Implement token counting using tiktoken
        # import tiktoken
        # model_name = model or self.model_default
        # encoding = tiktoken.encoding_for_model(model_name)
        # return len(encoding.encode(text))
        raise NotImplementedError("Token counting not implemented for OpenAI yet")


__all__ = ["OpenAIClient"]
