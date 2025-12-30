"""
AI Provider Interface and Response Models.

This module defines the base abstractions for multi-AI provider support,
allowing the application to work with different AI providers (OpenAI, Gemini, Claude, etc.)
through a unified interface.
"""

from typing import Optional, Protocol, Any
from pydantic import BaseModel, Field, ConfigDict


class AIResponse(BaseModel):
    """
    Unified response model for all AI providers.
    
    This model standardizes the response format across different AI providers,
    making it easier to switch between providers without changing application logic.
    
    Attributes:
        text: The generated text response from the AI model
        raw: Raw response object from the provider (for debugging/logging)
        provider: Name of the AI provider (e.g., 'openai', 'gemini', 'claude')
        model: Specific model used (e.g., 'gpt-4o-mini', 'gemini-1.5-flash')
        prompt_tokens: Number of tokens in the prompt (if available)
        completion_tokens: Number of tokens in the completion (if available)
        total_tokens: Total tokens used (prompt + completion)
    """
    
    text: str = Field(..., description="Generated text response")
    raw: Optional[dict] = Field(None, description="Raw provider response")
    provider: str = Field(..., description="Provider name (openai, gemini, claude)")
    model: str = Field(..., description="Model name used for generation")
    prompt_tokens: Optional[int] = Field(None, description="Tokens in prompt")
    completion_tokens: Optional[int] = Field(None, description="Tokens in completion")
    total_tokens: Optional[int] = Field(None, description="Total tokens used")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "text": "This is a generated response",
                "provider": "openai",
                "model": "gpt-4o-mini",
                "prompt_tokens": 50,
                "completion_tokens": 100,
                "total_tokens": 150
            }
        }
    )


class AIProvider(Protocol):
    """
    Protocol defining the interface that all AI providers must implement.
    
    This protocol ensures that all AI providers (OpenAI, Gemini, Claude, etc.)
    expose a consistent API, allowing them to be used interchangeably.
    
    Attributes:
        name: Provider identifier (e.g., 'openai', 'gemini', 'claude')
    """
    
    name: str
    
    async def generate(self, prompt: str, **kwargs: Any) -> AIResponse:
        """
        Generate text completion based on the given prompt.
        
        Args:
            prompt: The text prompt to send to the AI model
            **kwargs: Provider-specific parameters (temperature, max_tokens, etc.)
            
        Returns:
            AIResponse: Standardized response containing generated text and metadata
            
        Raises:
            Exception: Provider-specific exceptions for API errors, rate limits, etc.
        """
        ...
    
    async def embed(self, text: str, **kwargs: Any) -> list[float]:
        """
        Generate embeddings for the given text.
        
        Args:
            text: The text to embed
            **kwargs: Provider-specific parameters
            
        Returns:
            list[float]: Vector representation of the text
            
        Raises:
            NotImplementedError: If provider doesn't support embeddings
        """
        ...
    
    async def count_tokens(self, text: str, **kwargs: Any) -> int:
        """
        Count the number of tokens in the given text.
        
        Args:
            text: The text to tokenize
            **kwargs: Provider-specific parameters (model name, etc.)
            
        Returns:
            int: Number of tokens
            
        Note:
            Token counting may vary between providers due to different tokenizers.
        """
        ...


# Type alias for convenience
AIProviderType = AIProvider


__all__ = [
    "AIResponse",
    "AIProvider",
    "AIProviderType",
]
