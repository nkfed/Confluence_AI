"""
AI Settings Configuration Module.

Centralizes all AI provider settings, models, API keys, and routing configuration.
"""

import os
from typing import Optional, Literal, Tuple
from pydantic import BaseModel, Field


class AISettings(BaseModel):
    """
    Centralized AI configuration settings.
    
    Manages API keys, models, and routing modes for all AI providers.
    
    Routing Modes:
    - Mode A: OpenAI primary, Gemini fallback (quality-first)
    - Mode B: Gemini primary, OpenAI fallback (cost-first)
    - Mode C: Custom per-agent routing (balanced)
    - Mode D: A/B testing mode (comparison)
    """
    
    # Routing Configuration
    AI_ROUTING_MODE: Literal["A", "B", "C", "D"] = Field(
        default="A",
        description="AI routing mode: A=OpenAI→Gemini, B=Gemini→OpenAI, C=Custom, D=A/B Testing"
    )
    
    # OpenAI Configuration
    OPENAI_API_KEY: Optional[str] = Field(
        default=None,
        description="OpenAI API key"
    )
    OPENAI_MODEL: str = Field(
        default="gpt-4o-mini",
        description="Default OpenAI model"
    )
    
    # Google Gemini Configuration
    GEMINI_API_KEY: Optional[str] = Field(
        default=None,
        description="Google Gemini API key"
    )
    GEMINI_MODEL: str = Field(
        default="gemini-2.0-flash-exp",
        description="Default Gemini model"
    )
    
    # Router Default Settings
    DEFAULT_AI_PROVIDER: str = Field(
        default="openai",
        description="Default AI provider (openai, gemini)"
    )
    FALLBACK_AI_PROVIDER: Optional[str] = Field(
        default="gemini",
        description="Fallback AI provider if primary fails"
    )
    
    class Config:
        """Pydantic model configuration"""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
    
    def __init__(self, **data):
        """Initialize settings from environment variables"""
        # Override with environment variables if present
        env_data = {
            "AI_ROUTING_MODE": os.getenv("AI_ROUTING_MODE", "A"),
            "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
            "OPENAI_MODEL": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY"),
            "GEMINI_MODEL": os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp"),
            "DEFAULT_AI_PROVIDER": os.getenv("DEFAULT_AI_PROVIDER", "openai"),
            "FALLBACK_AI_PROVIDER": os.getenv("FALLBACK_AI_PROVIDER", "gemini"),
        }
        # Merge with provided data (provided data takes precedence)
        env_data.update(data)
        super().__init__(**env_data)
    
    def get_router_config(self) -> Tuple[str, Optional[str]]:
        """
        Get router configuration based on AI_ROUTING_MODE.
        
        Returns:
            Tuple[str, Optional[str]]: (primary_provider, fallback_provider)
        
        Routing Modes:
        - Mode A: OpenAI primary, Gemini fallback
          Best for: Quality-first applications, production stability
          
        - Mode B: Gemini primary, OpenAI fallback
          Best for: Cost optimization, bulk operations
          
        - Mode C: Custom routing per agent
          Best for: Balanced approach, different providers for different tasks
          Uses DEFAULT_AI_PROVIDER and FALLBACK_AI_PROVIDER from config
          
        - Mode D: A/B testing mode
          Best for: Comparing providers, quality analysis
          Uses DEFAULT_AI_PROVIDER and FALLBACK_AI_PROVIDER from config
        
        Example:
            >>> settings = AISettings(AI_ROUTING_MODE="A")
            >>> primary, fallback = settings.get_router_config()
            >>> print(f"Primary: {primary}, Fallback: {fallback}")
            Primary: openai, Fallback: gemini
        """
        match self.AI_ROUTING_MODE:
            case "A":
                # Mode A: OpenAI → Gemini (Quality First)
                return ("openai", "gemini")
            
            case "B":
                # Mode B: Gemini → OpenAI (Cost First)
                return ("gemini", "openai")
            
            case "C":
                # Mode C: Custom routing (Balanced)
                return (self.DEFAULT_AI_PROVIDER, self.FALLBACK_AI_PROVIDER)
            
            case "D":
                # Mode D: A/B Testing
                return (self.DEFAULT_AI_PROVIDER, self.FALLBACK_AI_PROVIDER)
            
            case _:
                # Fallback to custom settings
                return (self.DEFAULT_AI_PROVIDER, self.FALLBACK_AI_PROVIDER)
    
    def validate_config(self) -> dict:
        """
        Validate AI configuration and return status.
        
        Returns:
            dict: Configuration status with available providers
        """
        status = {
            "routing_mode": self.AI_ROUTING_MODE,
            "primary_provider": None,
            "fallback_provider": None,
            "openai_available": bool(self.OPENAI_API_KEY),
            "gemini_available": bool(self.GEMINI_API_KEY),
            "warnings": []
        }
        
        primary, fallback = self.get_router_config()
        status["primary_provider"] = primary
        status["fallback_provider"] = fallback
        
        # Check if primary provider is available
        if primary == "openai" and not self.OPENAI_API_KEY:
            status["warnings"].append("Primary provider OpenAI is not configured (missing API key)")
        
        if primary == "gemini" and not self.GEMINI_API_KEY:
            status["warnings"].append("Primary provider Gemini is not configured (missing API key)")
        
        # Check if fallback provider is available
        if fallback == "openai" and not self.OPENAI_API_KEY:
            status["warnings"].append("Fallback provider OpenAI is not configured (missing API key)")
        
        if fallback == "gemini" and not self.GEMINI_API_KEY:
            status["warnings"].append("Fallback provider Gemini is not configured (missing API key)")
        
        return status
    
    def get_model_for_provider(self, provider: str) -> str:
        """
        Get the configured model for a specific provider.
        
        Args:
            provider: Provider name ('openai' or 'gemini')
            
        Returns:
            str: Model name
        """
        if provider == "openai":
            return self.OPENAI_MODEL
        elif provider == "gemini":
            return self.GEMINI_MODEL
        else:
            return self.OPENAI_MODEL  # Default


# Global settings instance
settings = AISettings()


__all__ = ["AISettings", "settings"]
