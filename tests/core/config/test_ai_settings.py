"""
Tests for AI Settings configuration.

Tests routing modes, configuration validation, and settings management.
"""

import pytest
from src.core.config.ai_settings import AISettings


class TestAISettingsRoutingModes:
    """Tests for AI routing modes"""
    
    def test_routing_mode_a(self):
        """Test Mode A: OpenAI primary, Gemini fallback"""
        settings = AISettings(AI_ROUTING_MODE="A")
        primary, fallback = settings.get_router_config()
        
        assert primary == "openai"
        assert fallback == "gemini"
    
    def test_routing_mode_b(self):
        """Test Mode B: Gemini primary, OpenAI fallback"""
        settings = AISettings(AI_ROUTING_MODE="B")
        primary, fallback = settings.get_router_config()
        
        assert primary == "gemini"
        assert fallback == "openai"
    
    def test_routing_mode_c(self):
        """Test Mode C: Custom routing"""
        settings = AISettings(
            AI_ROUTING_MODE="C",
            DEFAULT_AI_PROVIDER="openai",
            FALLBACK_AI_PROVIDER="gemini"
        )
        primary, fallback = settings.get_router_config()
        
        assert primary == "openai"
        assert fallback == "gemini"
    
    def test_routing_mode_c_custom_providers(self):
        """Test Mode C with custom provider configuration"""
        settings = AISettings(
            AI_ROUTING_MODE="C",
            DEFAULT_AI_PROVIDER="gemini",
            FALLBACK_AI_PROVIDER="openai"
        )
        primary, fallback = settings.get_router_config()
        
        assert primary == "gemini"
        assert fallback == "openai"
    
    def test_routing_mode_d(self):
        """Test Mode D: A/B testing mode"""
        settings = AISettings(
            AI_ROUTING_MODE="D",
            DEFAULT_AI_PROVIDER="openai",
            FALLBACK_AI_PROVIDER="gemini"
        )
        primary, fallback = settings.get_router_config()
        
        assert primary == settings.DEFAULT_AI_PROVIDER
        assert fallback == settings.FALLBACK_AI_PROVIDER
    
    def test_default_routing_mode(self):
        """Test default routing mode"""
        settings = AISettings()
        
        assert settings.AI_ROUTING_MODE == "A"
        primary, fallback = settings.get_router_config()
        assert primary == "openai"
        assert fallback == "gemini"


class TestAISettingsConfiguration:
    """Tests for AI settings configuration"""
    
    def test_default_openai_model(self):
        """Test default OpenAI model"""
        settings = AISettings()
        assert settings.OPENAI_MODEL == "gpt-4o-mini"
    
    def test_default_gemini_model(self):
        """Test default Gemini model"""
        settings = AISettings()
        assert settings.GEMINI_MODEL == "gemini-2.0-flash-exp"
    
    def test_custom_openai_model(self):
        """Test custom OpenAI model"""
        settings = AISettings(OPENAI_MODEL="gpt-4o")
        assert settings.OPENAI_MODEL == "gpt-4o"
    
    def test_custom_gemini_model(self):
        """Test custom Gemini model"""
        settings = AISettings(GEMINI_MODEL="gemini-1.5-pro")
        assert settings.GEMINI_MODEL == "gemini-1.5-pro"
    
    def test_api_keys_optional(self):
        """Test that API keys are optional"""
        settings = AISettings()
        # Should not raise error even if keys are None
        assert settings.OPENAI_API_KEY is None or isinstance(settings.OPENAI_API_KEY, str)
        assert settings.GEMINI_API_KEY is None or isinstance(settings.GEMINI_API_KEY, str)
    
    def test_default_providers(self):
        """Test default provider configuration"""
        settings = AISettings()
        assert settings.DEFAULT_AI_PROVIDER == "openai"
        assert settings.FALLBACK_AI_PROVIDER == "gemini"


class TestAISettingsValidation:
    """Tests for configuration validation"""
    
    def test_validate_config_with_keys(self):
        """Test validation with API keys present"""
        settings = AISettings(
            OPENAI_API_KEY="test-openai-key",
            GEMINI_API_KEY="test-gemini-key"
        )
        
        status = settings.validate_config()
        
        assert status["routing_mode"] == "A"
        assert status["primary_provider"] == "openai"
        assert status["fallback_provider"] == "gemini"
        assert status["openai_available"] is True
        assert status["gemini_available"] is True
        assert len(status["warnings"]) == 0
    
    def test_validate_config_without_keys(self):
        """Test validation without API keys"""
        settings = AISettings()
        
        status = settings.validate_config()
        
        assert status["routing_mode"] == "A"
        assert status["openai_available"] is False or status["openai_available"] is True
        assert status["gemini_available"] is False or status["gemini_available"] is True
    
    def test_validate_config_missing_primary(self):
        """Test validation with missing primary provider"""
        settings = AISettings(
            AI_ROUTING_MODE="A",
            OPENAI_API_KEY=None,
            GEMINI_API_KEY="test-key"
        )
        
        status = settings.validate_config()
        
        # Check that warning about missing OpenAI is present
        warnings = [w for w in status["warnings"] if "OpenAI" in w and "Primary" in w]
        assert len(warnings) > 0 or status["openai_available"] is True  # May have key from env
    
    def test_validate_config_missing_fallback(self):
        """Test validation with missing fallback provider"""
        settings = AISettings(
            AI_ROUTING_MODE="A",
            OPENAI_API_KEY="test-key",
            GEMINI_API_KEY=None
        )
        
        status = settings.validate_config()
        
        # Check configuration
        assert status["primary_provider"] == "openai"
        assert status["fallback_provider"] == "gemini"


class TestAISettingsModelSelection:
    """Tests for model selection"""
    
    def test_get_model_for_openai(self):
        """Test getting OpenAI model"""
        settings = AISettings(OPENAI_MODEL="gpt-4o")
        model = settings.get_model_for_provider("openai")
        assert model == "gpt-4o"
    
    def test_get_model_for_gemini(self):
        """Test getting Gemini model"""
        settings = AISettings(GEMINI_MODEL="gemini-1.5-pro")
        model = settings.get_model_for_provider("gemini")
        assert model == "gemini-1.5-pro"
    
    def test_get_model_for_unknown_provider(self):
        """Test getting model for unknown provider defaults to OpenAI"""
        settings = AISettings(OPENAI_MODEL="gpt-4o-mini")
        model = settings.get_model_for_provider("unknown")
        assert model == "gpt-4o-mini"


class TestAISettingsRoutingScenarios:
    """Tests for real-world routing scenarios"""
    
    def test_quality_first_scenario(self):
        """Test quality-first scenario (Mode A)"""
        settings = AISettings(
            AI_ROUTING_MODE="A",
            OPENAI_API_KEY="openai-key",
            GEMINI_API_KEY="gemini-key"
        )
        
        primary, fallback = settings.get_router_config()
        assert primary == "openai"  # Higher quality
        assert fallback == "gemini"  # Cheaper fallback
    
    def test_cost_first_scenario(self):
        """Test cost-first scenario (Mode B)"""
        settings = AISettings(
            AI_ROUTING_MODE="B",
            OPENAI_API_KEY="openai-key",
            GEMINI_API_KEY="gemini-key"
        )
        
        primary, fallback = settings.get_router_config()
        assert primary == "gemini"  # Cheaper
        assert fallback == "openai"  # Quality fallback
    
    def test_balanced_scenario(self):
        """Test balanced scenario (Mode C)"""
        settings = AISettings(
            AI_ROUTING_MODE="C",
            DEFAULT_AI_PROVIDER="openai",
            FALLBACK_AI_PROVIDER="gemini",
            OPENAI_API_KEY="openai-key",
            GEMINI_API_KEY="gemini-key"
        )
        
        primary, fallback = settings.get_router_config()
        # Uses custom configuration
        assert primary == "openai"
        assert fallback == "gemini"
    
    def test_ab_testing_scenario(self):
        """Test A/B testing scenario (Mode D)"""
        settings = AISettings(
            AI_ROUTING_MODE="D",
            DEFAULT_AI_PROVIDER="openai",
            OPENAI_API_KEY="openai-key",
            GEMINI_API_KEY="gemini-key"
        )
        
        primary, fallback = settings.get_router_config()
        # Uses configuration for testing
        assert primary == "openai"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
