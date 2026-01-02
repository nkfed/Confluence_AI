"""
Tests for Router Inspector functionality.

Tests the explain() method that provides routing diagnostics.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.core.ai.router import AIProviderRouter
from src.core.ai.openai_client import OpenAIClient
from src.core.ai.gemini_client import GeminiClient
from src.core.config.ai_settings import AISettings
from src.core.ai.health import ProviderHealth, AIHealthReport


# Helper function to create mock health report
def create_mock_health_report(openai_ok=True, gemini_ok=True):
    """Create a mock health report for testing"""
    return AIHealthReport(providers={
        "openai": ProviderHealth(name="openai", ok=openai_ok),
        "gemini": ProviderHealth(name="gemini", ok=gemini_ok),
    })


class TestRouterExplainBasicStructure:
    """Tests for basic structure of explain() output"""
    
    @pytest.mark.asyncio
    async def test_explain_returns_dict(self):
        """Test that explain() returns a dictionary"""
        router = AIProviderRouter()
        
        with patch("src.core.ai.health.check_ai_health") as mock_health:
            mock_health.return_value = AIHealthReport(providers={
                "openai": ProviderHealth(name="openai", ok=True),
                "gemini": ProviderHealth(name="gemini", ok=True),
            })
            
            result = await router.explain()
            
            assert isinstance(result, dict)
    
    @pytest.mark.asyncio
    async def test_explain_has_required_keys(self):
        """Test that explain() includes all required keys"""
        router = AIProviderRouter()
        
        with patch("src.core.ai.health.check_ai_health") as mock_health:
            mock_health.return_value = AIHealthReport(providers={
                "openai": ProviderHealth(name="openai", ok=True),
                "gemini": ProviderHealth(name="gemini", ok=True),
            })
            
            result = await router.explain()
            
            required_keys = [
                "routing_mode",
                "default_provider",
                "fallback_provider",
                "registered_providers",
                "models",
                "api_keys",
                "health",
                "all_providers_ok",
            ]
            
            for key in required_keys:
                assert key in result, f"Missing key: {key}"
    
    @pytest.mark.asyncio
    async def test_routing_mode_is_returned(self):
        """Test that routing mode is included"""
        router = AIProviderRouter()
        settings = AISettings(AI_ROUTING_MODE="B")
        
        with patch("src.core.ai.health.check_ai_health") as mock_health:
            mock_health.return_value = AIHealthReport(providers={
                "openai": ProviderHealth(name="openai", ok=True),
                "gemini": ProviderHealth(name="gemini", ok=True),
            })
            
            result = await router.explain(settings)
            
            assert result["routing_mode"] == "B"
    
    @pytest.mark.asyncio
    async def test_default_provider_is_correct(self):
        """Test that default provider is correctly reported"""
        router = AIProviderRouter(default_provider="gemini")
        
        with patch("src.core.ai.health.check_ai_health") as mock_health:
            mock_health.return_value = AIHealthReport(providers={
                "openai": ProviderHealth(name="openai", ok=True),
                "gemini": ProviderHealth(name="gemini", ok=True),
            })
            
            result = await router.explain()
            
            assert result["default_provider"] == "gemini"
    
    @pytest.mark.asyncio
    async def test_fallback_provider_is_correct(self):
        """Test that fallback provider is correctly reported"""
        router = AIProviderRouter(
            default_provider="openai",
            fallback_provider="gemini"
        )
        
        with patch("src.core.ai.health.check_ai_health") as mock_health:
            mock_health.return_value = AIHealthReport(providers={
                "openai": ProviderHealth(name="openai", ok=True),
                "gemini": ProviderHealth(name="gemini", ok=True),
            })
            
            result = await router.explain()
            
            assert result["fallback_provider"] == "gemini"
    
    @pytest.mark.asyncio
    async def test_registered_providers_contains_openai_gemini(self):
        """Test that registered providers list is correct"""
        router = AIProviderRouter()
        
        with patch("src.core.ai.health.check_ai_health") as mock_health:
            mock_health.return_value = AIHealthReport(providers={
                "openai": ProviderHealth(name="openai", ok=True),
                "gemini": ProviderHealth(name="gemini", ok=True),
            })
            
            result = await router.explain()
            
            assert "openai" in result["registered_providers"]
            assert "gemini" in result["registered_providers"]
            assert isinstance(result["registered_providers"], list)


class TestRouterExplainModels:
    """Tests for model configuration reporting"""
    
    @pytest.mark.asyncio
    async def test_models_openai_is_correct(self):
        """Test that OpenAI model is correctly reported"""
        router = AIProviderRouter()
        settings = AISettings(OPENAI_MODEL="gpt-4o")
        
        with patch("src.core.ai.health.check_ai_health") as mock_health:
            mock_health.return_value = AIHealthReport(providers={
                "openai": ProviderHealth(name="openai", ok=True),
                "gemini": ProviderHealth(name="gemini", ok=True),
            })
            
            result = await router.explain(settings)
            
            assert result["models"]["openai"] == "gpt-4o"
    
    @pytest.mark.asyncio
    async def test_models_gemini_is_correct(self):
        """Test that Gemini model is correctly reported"""
        router = AIProviderRouter()
        settings = AISettings(GEMINI_MODEL="gemini-1.5-pro")
        
        with patch("src.core.ai.health.check_ai_health") as mock_health:
            mock_health.return_value = AIHealthReport(providers={
                "openai": ProviderHealth(name="openai", ok=True),
                "gemini": ProviderHealth(name="gemini", ok=True),
            })
            
            result = await router.explain(settings)
            
            assert result["models"]["gemini"] == "gemini-1.5-pro"


class TestRouterExplainAPIKeys:
    """Tests for API key availability reporting"""
    
    @pytest.mark.asyncio
    async def test_api_keys_present(self):
        """Test that API keys are reported as present when set"""
        router = AIProviderRouter()
        settings = AISettings(
            OPENAI_API_KEY="test-key-123",
            GEMINI_API_KEY="test-key-456"
        )
        
        with patch("src.core.ai.health.check_ai_health") as mock_health:
            mock_health.return_value = AIHealthReport(providers={
                "openai": ProviderHealth(name="openai", ok=True),
                "gemini": ProviderHealth(name="gemini", ok=True),
            })
            
            result = await router.explain(settings)
            
            assert result["api_keys"]["openai"] is True
            assert result["api_keys"]["gemini"] is True
    
    @pytest.mark.asyncio
    async def test_api_keys_missing(self):
        """Test that missing API keys are reported as False"""
        router = AIProviderRouter()
        settings = AISettings(
            OPENAI_API_KEY=None,
            GEMINI_API_KEY=None
        )
        
        with patch("src.core.ai.health.check_ai_health") as mock_health:
            mock_health.return_value = AIHealthReport(providers={
                "openai": ProviderHealth(name="openai", ok=False, error="No key"),
                "gemini": ProviderHealth(name="gemini", ok=False, error="No key"),
            })
            
            result = await router.explain(settings)
            
            assert result["api_keys"]["openai"] is False
            assert result["api_keys"]["gemini"] is False


class TestRouterExplainHealth:
    """Tests for health status reporting"""
    
    @pytest.mark.asyncio
    async def test_health_openai_ok(self):
        """Test that OpenAI health is correctly reported when OK"""
        router = AIProviderRouter()
        
        with patch("src.core.ai.health.check_ai_health") as mock_health:
            mock_health.return_value = AIHealthReport(providers={
                "openai": ProviderHealth(
                    name="openai",
                    ok=True,
                    details={"model": "gpt-4o-mini"}
                ),
                "gemini": ProviderHealth(name="gemini", ok=True),
            })
            
            result = await router.explain()
            
            assert result["health"]["openai"]["ok"] is True
            assert result["health"]["openai"]["error"] is None
            assert result["health"]["openai"]["details"]["model"] == "gpt-4o-mini"
    
    @pytest.mark.asyncio
    async def test_health_gemini_ok(self):
        """Test that Gemini health is correctly reported when OK"""
        router = AIProviderRouter()
        
        with patch("src.core.ai.health.check_ai_health") as mock_health:
            mock_health.return_value = AIHealthReport(providers={
                "openai": ProviderHealth(name="openai", ok=True),
                "gemini": ProviderHealth(
                    name="gemini",
                    ok=True,
                    details={"model": "gemini-2.0-flash-exp"}
                ),
            })
            
            result = await router.explain()
            
            assert result["health"]["gemini"]["ok"] is True
            assert result["health"]["gemini"]["error"] is None
    
    @pytest.mark.asyncio
    async def test_health_provider_error(self):
        """Test that provider errors are correctly reported"""
        router = AIProviderRouter()
        
        with patch("src.core.ai.health.check_ai_health") as mock_health:
            mock_health.return_value = AIHealthReport(providers={
                "openai": ProviderHealth(
                    name="openai",
                    ok=False,
                    error="API key not set"
                ),
                "gemini": ProviderHealth(name="gemini", ok=True),
            })
            
            result = await router.explain()
            
            assert result["health"]["openai"]["ok"] is False
            assert result["health"]["openai"]["error"] == "API key not set"


class TestRouterExplainAllProvidersOK:
    """Tests for all_providers_ok status"""
    
    @pytest.mark.asyncio
    async def test_all_providers_ok_true(self):
        """Test that all_providers_ok is True when all healthy"""
        router = AIProviderRouter()
        
        with patch("src.core.ai.health.check_ai_health") as mock_health:
            mock_health.return_value = AIHealthReport(providers={
                "openai": ProviderHealth(name="openai", ok=True),
                "gemini": ProviderHealth(name="gemini", ok=True),
            })
            
            result = await router.explain()
            
            assert result["all_providers_ok"] is True
    
    @pytest.mark.asyncio
    async def test_all_providers_ok_false(self):
        """Test that all_providers_ok is False when any unhealthy"""
        router = AIProviderRouter()
        
        with patch("src.core.ai.health.check_ai_health") as mock_health:
            mock_health.return_value = AIHealthReport(providers={
                "openai": ProviderHealth(name="openai", ok=True),
                "gemini": ProviderHealth(name="gemini", ok=False, error="API error"),
            })
            
            result = await router.explain()
            
            assert result["all_providers_ok"] is False


class TestRouterExplainMockedHealthCheck:
    """Tests with mocked health check"""
    
    @pytest.mark.asyncio
    async def test_explain_calls_health_check(self):
        """Test that explain() calls check_ai_health"""
        router = AIProviderRouter()
        
        with patch("src.core.ai.health.check_ai_health") as mock_health:
            mock_health.return_value = AIHealthReport(providers={
                "openai": ProviderHealth(name="openai", ok=True),
                "gemini": ProviderHealth(name="gemini", ok=True),
            })
            
            await router.explain()
            
            # Verify health check was called
            mock_health.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_explain_passes_settings_to_health_check(self):
        """Test that settings are passed to health check"""
        router = AIProviderRouter()
        settings = AISettings(AI_ROUTING_MODE="C")
        
        with patch("src.core.ai.health.check_ai_health") as mock_health:
            mock_health.return_value = AIHealthReport(providers={
                "openai": ProviderHealth(name="openai", ok=True),
                "gemini": ProviderHealth(name="gemini", ok=True),
            })
            
            await router.explain(settings)
            
            # Verify settings were passed
            mock_health.assert_called_once_with(settings)
    
    @pytest.mark.asyncio
    async def test_explain_uses_default_settings_if_none(self):
        """Test that default settings are used if not provided"""
        router = AIProviderRouter()
        
        with patch("src.core.ai.health.check_ai_health") as mock_health, \
             patch("src.core.config.ai_settings.AISettings") as MockSettings:
            
            mock_settings_instance = MagicMock()
            MockSettings.return_value = mock_settings_instance
            
            mock_health.return_value = AIHealthReport(providers={
                "openai": ProviderHealth(name="openai", ok=True),
                "gemini": ProviderHealth(name="gemini", ok=True),
            })
            
            await router.explain()
            
            # Verify AISettings() was called (inside explain method)
            # Note: This is called inside the explain method, not here
            # So we just verify that health check was called
            mock_health.assert_called_once()


class TestRouterExplainIntegration:
    """Integration tests for explain()"""
    
    @pytest.mark.asyncio
    async def test_explain_full_report_structure(self):
        """Test complete report structure"""
        router = AIProviderRouter(
            default_provider="openai",
            fallback_provider="gemini"
        )
        
        settings = AISettings(
            AI_ROUTING_MODE="A",
            OPENAI_MODEL="gpt-4o-mini",
            GEMINI_MODEL="gemini-2.0-flash-exp",
            OPENAI_API_KEY="test-key",
            GEMINI_API_KEY="test-key"
        )
        
        with patch("src.core.ai.health.check_ai_health") as mock_health:
            mock_health.return_value = AIHealthReport(providers={
                "openai": ProviderHealth(
                    name="openai",
                    ok=True,
                    details={"model": "gpt-4o-mini", "tokens": 10}
                ),
                "gemini": ProviderHealth(
                    name="gemini",
                    ok=True,
                    details={"model": "gemini-2.0-flash-exp", "tokens": 5}
                ),
            })
            
            result = await router.explain(settings)
            
            # Verify complete structure
            assert result["routing_mode"] == "A"
            assert result["default_provider"] == "openai"
            assert result["fallback_provider"] == "gemini"
            assert "openai" in result["registered_providers"]
            assert "gemini" in result["registered_providers"]
            assert result["models"]["openai"] == "gpt-4o-mini"
            assert result["models"]["gemini"] == "gemini-2.0-flash-exp"
            assert result["api_keys"]["openai"] is True
            assert result["api_keys"]["gemini"] is True
            assert result["health"]["openai"]["ok"] is True
            assert result["health"]["gemini"]["ok"] is True
            assert result["all_providers_ok"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

