"""
Tests for Cost Tracking functionality.

Tests cost calculation for OpenAI and Gemini providers.
"""

import pytest
from src.core.ai.costs import CostConfig, CostEstimate, CostCalculator


class TestCostConfig:
    """Tests for CostConfig dataclass"""
    
    def test_default_config(self):
        """Test default cost configuration"""
        config = CostConfig()
        
        # OpenAI pricing
        assert config.openai_prompt_per_1k == 0.00015
        assert config.openai_completion_per_1k == 0.0006
        
        # Gemini pricing
        assert config.gemini_prompt_per_1k == 0.000075
        assert config.gemini_completion_per_1k == 0.0003
    
    def test_custom_config(self):
        """Test custom cost configuration"""
        config = CostConfig(
            openai_prompt_per_1k=0.001,
            openai_completion_per_1k=0.002,
            gemini_prompt_per_1k=0.0005,
            gemini_completion_per_1k=0.001,
        )
        
        assert config.openai_prompt_per_1k == 0.001
        assert config.openai_completion_per_1k == 0.002
        assert config.gemini_prompt_per_1k == 0.0005
        assert config.gemini_completion_per_1k == 0.001


class TestCostEstimate:
    """Tests for CostEstimate dataclass"""
    
    def test_cost_estimate_creation(self):
        """Test creating cost estimate"""
        estimate = CostEstimate(
            provider="openai",
            prompt_tokens=1000,
            completion_tokens=500,
            total_tokens=1500,
            prompt_cost_usd=0.00015,
            completion_cost_usd=0.0003,
            total_usd=0.00045,
        )
        
        assert estimate.provider == "openai"
        assert estimate.prompt_tokens == 1000
        assert estimate.completion_tokens == 500
        assert estimate.total_tokens == 1500
        assert estimate.total_usd == 0.00045
    
    def test_cost_estimate_string_repr(self):
        """Test string representation of cost estimate"""
        estimate = CostEstimate(
            provider="gemini",
            prompt_tokens=1000,
            completion_tokens=500,
            total_tokens=1500,
            prompt_cost_usd=0.000075,
            completion_cost_usd=0.00015,
            total_usd=0.000225,
        )
        
        str_repr = str(estimate)
        assert "gemini" in str_repr
        assert "1500" in str_repr
        assert "0.000225" in str_repr


class TestCostCalculator:
    """Tests for CostCalculator"""
    
    def test_initialization(self):
        """Test calculator initialization"""
        calculator = CostCalculator()
        
        assert calculator.config is not None
        assert isinstance(calculator.config, CostConfig)
    
    def test_initialization_with_custom_config(self):
        """Test calculator with custom config"""
        config = CostConfig(
            openai_prompt_per_1k=0.01,
            openai_completion_per_1k=0.02,
        )
        calculator = CostCalculator(config)
        
        assert calculator.config == config
        assert calculator.config.openai_prompt_per_1k == 0.01


class TestCostCalculatorOpenAI:
    """Tests for OpenAI cost calculations"""
    
    def test_openai_basic_calculation(self):
        """Test basic OpenAI cost calculation"""
        calculator = CostCalculator()
        
        # 1000 prompt + 500 completion tokens
        cost = calculator.estimate("openai", prompt_tokens=1000, completion_tokens=500)
        
        assert cost.provider == "openai"
        assert cost.prompt_tokens == 1000
        assert cost.completion_tokens == 500
        assert cost.total_tokens == 1500
        
        # Expected: (1000/1000 * 0.00015) + (500/1000 * 0.0006)
        # = 0.00015 + 0.0003 = 0.00045
        assert cost.prompt_cost_usd == pytest.approx(0.00015, abs=1e-8)
        assert cost.completion_cost_usd == pytest.approx(0.0003, abs=1e-8)
        assert cost.total_usd == pytest.approx(0.00045, abs=1e-8)
    
    def test_openai_zero_tokens(self):
        """Test OpenAI with zero tokens"""
        calculator = CostCalculator()
        
        cost = calculator.estimate("openai", prompt_tokens=0, completion_tokens=0)
        
        assert cost.total_usd == 0.0
        assert cost.prompt_cost_usd == 0.0
        assert cost.completion_cost_usd == 0.0
    
    def test_openai_large_tokens(self):
        """Test OpenAI with large token counts"""
        calculator = CostCalculator()
        
        # 100K prompt + 50K completion
        cost = calculator.estimate("openai", prompt_tokens=100000, completion_tokens=50000)
        
        # Expected: (100000/1000 * 0.00015) + (50000/1000 * 0.0006)
        # = 0.015 + 0.03 = 0.045
        assert cost.total_usd == pytest.approx(0.045, abs=1e-6)
    
    def test_openai_with_custom_pricing(self):
        """Test OpenAI with custom pricing"""
        config = CostConfig(
            openai_prompt_per_1k=0.001,
            openai_completion_per_1k=0.002,
        )
        calculator = CostCalculator(config)
        
        cost = calculator.estimate("openai", prompt_tokens=1000, completion_tokens=500)
        
        # Expected: (1000/1000 * 0.001) + (500/1000 * 0.002)
        # = 0.001 + 0.001 = 0.002
        assert cost.total_usd == pytest.approx(0.002, abs=1e-8)


class TestCostCalculatorGemini:
    """Tests for Gemini cost calculations"""
    
    def test_gemini_basic_calculation(self):
        """Test basic Gemini cost calculation"""
        calculator = CostCalculator()
        
        # 1000 prompt + 500 completion tokens
        cost = calculator.estimate("gemini", prompt_tokens=1000, completion_tokens=500)
        
        assert cost.provider == "gemini"
        assert cost.prompt_tokens == 1000
        assert cost.completion_tokens == 500
        assert cost.total_tokens == 1500
        
        # Expected: (1000/1000 * 0.000075) + (500/1000 * 0.0003)
        # = 0.000075 + 0.00015 = 0.000225
        assert cost.prompt_cost_usd == pytest.approx(0.000075, abs=1e-8)
        assert cost.completion_cost_usd == pytest.approx(0.00015, abs=1e-8)
        assert cost.total_usd == pytest.approx(0.000225, abs=1e-8)
    
    def test_gemini_zero_tokens(self):
        """Test Gemini with zero tokens"""
        calculator = CostCalculator()
        
        cost = calculator.estimate("gemini", prompt_tokens=0, completion_tokens=0)
        
        assert cost.total_usd == 0.0
    
    def test_gemini_large_tokens(self):
        """Test Gemini with large token counts"""
        calculator = CostCalculator()
        
        # 100K prompt + 50K completion
        cost = calculator.estimate("gemini", prompt_tokens=100000, completion_tokens=50000)
        
        # Expected: (100000/1000 * 0.000075) + (50000/1000 * 0.0003)
        # = 0.0075 + 0.015 = 0.0225
        assert cost.total_usd == pytest.approx(0.0225, abs=1e-6)


class TestCostCalculatorUnknownProvider:
    """Tests for unknown provider handling"""
    
    def test_unknown_provider_returns_zero(self):
        """Test that unknown provider returns zero cost"""
        calculator = CostCalculator()
        
        cost = calculator.estimate("unknown", prompt_tokens=1000, completion_tokens=500)  # type: ignore
        
        assert cost.provider == "unknown"
        assert cost.total_usd == 0.0
        assert cost.prompt_cost_usd == 0.0
        assert cost.completion_cost_usd == 0.0


class TestCostCalculatorComparison:
    """Tests for provider comparison"""
    
    def test_compare_providers(self):
        """Test comparing costs across providers"""
        calculator = CostCalculator()
        
        comparison = calculator.compare_providers(
            prompt_tokens=1000,
            completion_tokens=500
        )
        
        assert "openai" in comparison
        assert "gemini" in comparison
        
        openai_cost = comparison["openai"]
        gemini_cost = comparison["gemini"]
        
        # Verify OpenAI is more expensive than Gemini (with default pricing)
        assert openai_cost.total_usd > gemini_cost.total_usd
        
        # Verify exact costs
        assert openai_cost.total_usd == pytest.approx(0.00045, abs=1e-8)
        assert gemini_cost.total_usd == pytest.approx(0.000225, abs=1e-8)
    
    def test_get_savings_openai_to_gemini(self):
        """Test calculating savings when switching from OpenAI to Gemini"""
        calculator = CostCalculator()
        
        savings = calculator.get_savings(
            provider_a="openai",
            provider_b="gemini",
            prompt_tokens=1000,
            completion_tokens=500
        )
        
        assert savings["provider_a"] == "openai"
        assert savings["provider_b"] == "gemini"
        assert savings["cost_a_usd"] == pytest.approx(0.00045, abs=1e-8)
        assert savings["cost_b_usd"] == pytest.approx(0.000225, abs=1e-8)
        
        # Savings: 0.00045 - 0.000225 = 0.000225
        assert savings["absolute_usd"] == pytest.approx(0.000225, abs=1e-8)
        
        # Percentage: (0.000225 / 0.00045) * 100 = 50%
        assert savings["percentage"] == pytest.approx(50.0, abs=0.1)
        
        # Gemini is cheaper
        assert savings["cheaper"] == "gemini"
    
    def test_get_savings_gemini_to_openai(self):
        """Test calculating negative savings (more expensive)"""
        calculator = CostCalculator()
        
        savings = calculator.get_savings(
            provider_a="gemini",
            provider_b="openai",
            prompt_tokens=1000,
            completion_tokens=500
        )
        
        # Negative savings (more expensive)
        assert savings["absolute_usd"] < 0
        assert savings["cheaper"] == "gemini"
    
    def test_get_savings_zero_tokens(self):
        """Test savings calculation with zero tokens"""
        calculator = CostCalculator()
        
        savings = calculator.get_savings(
            provider_a="openai",
            provider_b="gemini",
            prompt_tokens=0,
            completion_tokens=0
        )
        
        assert savings["absolute_usd"] == 0.0
        assert savings["percentage"] == 0.0


class TestCostCalculatorRealWorldScenarios:
    """Tests for real-world usage scenarios"""
    
    def test_bulk_tagging_1000_pages(self):
        """Test cost for bulk tagging 1000 pages"""
        calculator = CostCalculator()
        
        # Average: 300 prompt tokens, 50 completion tokens per page
        tokens_per_page = (300, 50)
        num_pages = 1000
        
        # OpenAI cost
        openai_total = 0.0
        for _ in range(num_pages):
            cost = calculator.estimate("openai", *tokens_per_page)
            openai_total += cost.total_usd
        
        # Gemini cost
        gemini_total = 0.0
        for _ in range(num_pages):
            cost = calculator.estimate("gemini", *tokens_per_page)
            gemini_total += cost.total_usd
        
        # Verify Gemini is significantly cheaper
        assert gemini_total < openai_total
        savings = openai_total - gemini_total
        savings_percentage = (savings / openai_total) * 100
        
        # Should save around 50%
        assert savings_percentage > 40
    
    def test_summary_generation_100_pages(self):
        """Test cost for summary generation"""
        calculator = CostCalculator()
        
        # Average: 800 prompt tokens, 200 completion tokens per summary
        tokens_per_summary = (800, 200)
        num_summaries = 100
        
        openai_cost = calculator.estimate("openai", *tokens_per_summary)
        gemini_cost = calculator.estimate("gemini", *tokens_per_summary)
        
        openai_total = openai_cost.total_usd * num_summaries
        gemini_total = gemini_cost.total_usd * num_summaries
        
        # Log costs for analysis
        print(f"\nSummary generation (100 pages):")
        print(f"  OpenAI: ${openai_total:.4f}")
        print(f"  Gemini: ${gemini_total:.4f}")
        print(f"  Savings: ${openai_total - gemini_total:.4f}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
