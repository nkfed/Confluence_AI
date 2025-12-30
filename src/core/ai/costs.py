"""
Cost Tracking Module for AI Providers.

Calculates cost estimates for OpenAI and Gemini API calls based on token usage.
Useful for budget planning, cost optimization, and provider comparison.
"""

from dataclasses import dataclass
from typing import Literal, Optional
from src.core.logging.logger import get_logger

logger = get_logger(__name__)

ProviderName = Literal["openai", "gemini"]


@dataclass
class CostConfig:
    """
    Cost configuration in USD per 1000 tokens.
    
    Values are approximate and based on current pricing (Dec 2025):
    - OpenAI GPT-4o-mini: $0.150/1M input, $0.600/1M output
    - Google Gemini 2.0 Flash: $0.075/1M input, $0.30/1M output (free tier: 15 RPM)
    
    Attributes:
        openai_prompt_per_1k: Cost per 1000 prompt tokens for OpenAI
        openai_completion_per_1k: Cost per 1000 completion tokens for OpenAI
        gemini_prompt_per_1k: Cost per 1000 prompt tokens for Gemini
        gemini_completion_per_1k: Cost per 1000 completion tokens for Gemini
    """
    # OpenAI GPT-4o-mini pricing
    openai_prompt_per_1k: float = 0.00015      # $0.150 per 1M tokens
    openai_completion_per_1k: float = 0.0006   # $0.600 per 1M tokens
    
    # Google Gemini 2.0 Flash pricing
    gemini_prompt_per_1k: float = 0.000075     # $0.075 per 1M tokens
    gemini_completion_per_1k: float = 0.0003   # $0.300 per 1M tokens


@dataclass
class CostEstimate:
    """
    Cost estimate for a single AI request.
    
    Attributes:
        provider: AI provider name
        prompt_tokens: Number of prompt tokens
        completion_tokens: Number of completion tokens
        total_tokens: Total tokens (prompt + completion)
        prompt_cost_usd: Cost of prompt tokens in USD
        completion_cost_usd: Cost of completion tokens in USD
        total_usd: Total cost in USD
    """
    provider: ProviderName
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    prompt_cost_usd: float
    completion_cost_usd: float
    total_usd: float
    
    def __str__(self) -> str:
        """String representation of cost estimate."""
        return (
            f"CostEstimate({self.provider}: "
            f"${self.total_usd:.6f} for {self.total_tokens} tokens)"
        )


class CostCalculator:
    """
    Calculator for AI API cost estimation.
    
    Calculates costs for OpenAI and Gemini providers based on token usage.
    
    Example:
        >>> calculator = CostCalculator()
        >>> cost = calculator.estimate("openai", prompt_tokens=1200, completion_tokens=800)
        >>> print(f"Cost: ${cost.total_usd:.6f}")
        Cost: $0.000660
    """
    
    def __init__(self, config: Optional[CostConfig] = None):
        """
        Initialize cost calculator.
        
        Args:
            config: Cost configuration (uses default if not provided)
        """
        self.config = config or CostConfig()
        logger.debug(
            f"Cost calculator initialized: "
            f"OpenAI ${self.config.openai_prompt_per_1k:.6f}/${self.config.openai_completion_per_1k:.6f} per 1k, "
            f"Gemini ${self.config.gemini_prompt_per_1k:.6f}/${self.config.gemini_completion_per_1k:.6f} per 1k"
        )
    
    def estimate(
        self,
        provider: ProviderName,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> CostEstimate:
        """
        Calculate cost estimate for an AI request.
        
        Args:
            provider: AI provider name ('openai' or 'gemini')
            prompt_tokens: Number of prompt tokens
            completion_tokens: Number of completion tokens
            
        Returns:
            CostEstimate: Detailed cost breakdown
            
        Example:
            >>> calc = CostCalculator()
            >>> cost = calc.estimate("openai", 1000, 500)
            >>> print(f"Total: ${cost.total_usd:.6f}")
            Total: $0.000450
        """
        total_tokens = prompt_tokens + completion_tokens
        
        if provider == "openai":
            prompt_cost = (prompt_tokens / 1000.0) * self.config.openai_prompt_per_1k
            completion_cost = (completion_tokens / 1000.0) * self.config.openai_completion_per_1k
        
        elif provider == "gemini":
            prompt_cost = (prompt_tokens / 1000.0) * self.config.gemini_prompt_per_1k
            completion_cost = (completion_tokens / 1000.0) * self.config.gemini_completion_per_1k
        
        else:
            logger.warning(f"Unknown provider '{provider}', returning zero cost")
            prompt_cost = 0.0
            completion_cost = 0.0
        
        total_cost = prompt_cost + completion_cost
        
        estimate = CostEstimate(
            provider=provider,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            prompt_cost_usd=round(prompt_cost, 8),
            completion_cost_usd=round(completion_cost, 8),
            total_usd=round(total_cost, 8),
        )
        
        logger.debug(
            f"Cost estimate: {provider} - "
            f"{prompt_tokens}p + {completion_tokens}c = ${estimate.total_usd:.6f}"
        )
        
        return estimate
    
    def compare_providers(
        self,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> dict[ProviderName, CostEstimate]:
        """
        Compare costs across all providers for the same token usage.
        
        Args:
            prompt_tokens: Number of prompt tokens
            completion_tokens: Number of completion tokens
            
        Returns:
            dict: Cost estimates for each provider
            
        Example:
            >>> calc = CostCalculator()
            >>> comparison = calc.compare_providers(1000, 500)
            >>> for provider, cost in comparison.items():
            ...     print(f"{provider}: ${cost.total_usd:.6f}")
            openai: $0.000450
            gemini: $0.000225
        """
        return {
            "openai": self.estimate("openai", prompt_tokens, completion_tokens),
            "gemini": self.estimate("gemini", prompt_tokens, completion_tokens),
        }
    
    def get_savings(
        self,
        provider_a: ProviderName,
        provider_b: ProviderName,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> dict:
        """
        Calculate savings when switching from one provider to another.
        
        Args:
            provider_a: First provider
            provider_b: Second provider
            prompt_tokens: Number of prompt tokens
            completion_tokens: Number of completion tokens
            
        Returns:
            dict: Savings analysis
            
        Example:
            >>> calc = CostCalculator()
            >>> savings = calc.get_savings("openai", "gemini", 1000, 500)
            >>> print(f"Savings: ${savings['absolute_usd']:.6f} ({savings['percentage']:.1f}%)")
            Savings: $0.000225 (50.0%)
        """
        cost_a = self.estimate(provider_a, prompt_tokens, completion_tokens)
        cost_b = self.estimate(provider_b, prompt_tokens, completion_tokens)
        
        absolute_savings = cost_a.total_usd - cost_b.total_usd
        percentage_savings = (absolute_savings / cost_a.total_usd * 100) if cost_a.total_usd > 0 else 0
        
        return {
            "provider_a": provider_a,
            "provider_b": provider_b,
            "cost_a_usd": cost_a.total_usd,
            "cost_b_usd": cost_b.total_usd,
            "absolute_usd": round(absolute_savings, 8),
            "percentage": round(percentage_savings, 2),
            "cheaper": provider_b if absolute_savings > 0 else provider_a,
        }


__all__ = ["CostConfig", "CostEstimate", "CostCalculator"]
