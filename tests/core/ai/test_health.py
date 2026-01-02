"""
Tests for AI Provider Health Check.

Tests health check functionality for OpenAI and Gemini providers.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.core.ai.health import (
    ProviderHealth,
    AIHealthReport,
    check_provider_openai,
    check_provider_gemini,
    check_ai_health,
)
from src.core.config.ai_settings import AISettings
from src.core.ai.interface import AIResponse


class TestProviderHealth:
    """Tests for ProviderHealth dataclass"""
    
    def test_provider_health_ok(self):
        """Test healthy provider"""
        health = ProviderHealth(name="openai", ok=True)
        assert health.name == "openai"
        assert health.ok is True
        assert health.error is None
    
    def test_provider_health_error(self):
        """Test unhealthy provider with error"""
        health = ProviderHealth(
            name="gemini",
            ok=False,
            error="API key not set"
        )
        assert health.name == "gemini"
        assert health.ok is False
        assert health.error == "API key not set"
    
    def test_provider_health_with_details(self):
        """Test provider health with details"""
        health = ProviderHealth(
            name="openai",
            ok=True,
            details={"model": "gpt-4o-mini", "tokens": 10}
        )
        assert health.details["model"] == "gpt-4o-mini"
        assert health.details["tokens"] == 10


class TestAIHealthReport:
    """Tests for AIHealthReport dataclass"""
    
    def test_all_ok_true(self):
        """Test all_ok when all providers healthy"""
        report = AIHealthReport(
            providers={
                "openai": ProviderHealth(name="openai", ok=True),
                "gemini": ProviderHealth(name="gemini", ok=True),
            }
        )
        assert report.all_ok is True
    
    def test_all_ok_false(self):
        """Test all_ok when some providers unhealthy"""
        report = AIHealthReport(
            providers={
                "openai": ProviderHealth(name="openai", ok=True),
                "gemini": ProviderHealth(name="gemini", ok=False, error="API error"),
            }
        )
        assert report.all_ok is False
    
    def test_healthy_providers(self):
        """Test healthy_providers property"""
        report = AIHealthReport(
            providers={
                "openai": ProviderHealth(name="openai", ok=True),
                "gemini": ProviderHealth(name="gemini", ok=False),
            }
        )
        assert report.healthy_providers == ["openai"]
    
    def test_unhealthy_providers(self):
        """Test unhealthy_providers property"""
        report = AIHealthReport(
            providers={
                "openai": ProviderHealth(name="openai", ok=False),
                "gemini": ProviderHealth(name="gemini", ok=True),
            }
        )
        assert report.unhealthy_providers == ["openai"]


class TestCheckProviderOpenAI:
    """Tests for OpenAI provider health check"""
    
    @pytest.mark.asyncio
    async def test_openai_missing_api_key(self):
        """Test OpenAI health check with missing API key"""
        settings = AISettings(OPENAI_API_KEY=None)
        
        health = await check_provider_openai(settings)
        
        assert health.name == "openai"
        assert health.ok is False
        assert "not set" in health.error
    
    @pytest.mark.asyncio
    async def test_openai_healthy(self):
        """Test OpenAI health check with successful response"""
        settings = AISettings(
            OPENAI_API_KEY="test-key",
            OPENAI_MODEL="gpt-4o-mini"
        )
        
        mock_response = AIResponse(
            text="pong",
            provider="openai",
            model="gpt-4o-mini",
            total_tokens=5
        )
        
        with patch("src.core.ai.health.OpenAIClient") as MockClient:
            mock_client = MockClient.return_value
            mock_client.generate = AsyncMock(return_value=mock_response)
            
            health = await check_provider_openai(settings)
        
        assert health.name == "openai"
        assert health.ok is True
        assert health.error is None
        assert health.details["model"] == "gpt-4o-mini"
        assert health.details["total_tokens"] == 5
    
    @pytest.mark.asyncio
    async def test_openai_api_error(self):
        """Test OpenAI health check with API error"""
        settings = AISettings(OPENAI_API_KEY="test-key")
        
        with patch("src.core.ai.health.OpenAIClient") as MockClient:
            mock_client = MockClient.return_value
            mock_client.generate = AsyncMock(
                side_effect=RuntimeError("API rate limit")
            )
            
            health = await check_provider_openai(settings)
        
        assert health.name == "openai"
        assert health.ok is False
        assert "rate limit" in health.error


class TestCheckProviderGemini:
    """Tests for Gemini provider health check"""
    
    @pytest.mark.asyncio
    async def test_gemini_missing_api_key(self):
        """Test Gemini health check with missing API key"""
        settings = AISettings(GEMINI_API_KEY=None)
        
        health = await check_provider_gemini(settings)
        
        assert health.name == "gemini"
        assert health.ok is False
        assert "not set" in health.error
    
    @pytest.mark.asyncio
    async def test_gemini_healthy(self):
        """Test Gemini health check with successful response"""
        settings = AISettings(
            GEMINI_API_KEY="test-key",
            GEMINI_MODEL="gemini-2.0-flash-exp"
        )
        
        with patch("src.core.ai.health.GeminiClient") as MockClient:
            mock_client = MagicMock()
            mock_client.count_tokens = AsyncMock(return_value=4)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            
            MockClient.return_value = mock_client
            
            health = await check_provider_gemini(settings)
        
        assert health.name == "gemini"
        assert health.ok is True
        assert health.error is None
        assert health.details["model"] == "gemini-2.0-flash-exp"
        assert health.details["tokens_for_ping"] == 4
    
    @pytest.mark.asyncio
    async def test_gemini_api_error(self):
        """Test Gemini health check with API error"""
        settings = AISettings(GEMINI_API_KEY="test-key")
        
        with patch("src.core.ai.health.GeminiClient") as MockClient:
            mock_client = MagicMock()
            mock_client.count_tokens = AsyncMock(
                side_effect=RuntimeError("Invalid API key")
            )
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            
            MockClient.return_value = mock_client
            
            health = await check_provider_gemini(settings)
        
        assert health.name == "gemini"
        assert health.ok is False
        assert "Invalid API key" in health.error


class TestCheckAIHealth:
    """Tests for complete AI health check"""
    
    @pytest.mark.asyncio
    async def test_all_providers_healthy(self):
        """Test health check with all providers healthy"""
        settings = AISettings(
            OPENAI_API_KEY="openai-key",
            GEMINI_API_KEY="gemini-key"
        )
        
        # Mock OpenAI
        openai_response = AIResponse(
            text="pong",
            provider="openai",
            model="gpt-4o-mini",
            total_tokens=5
        )
        
        with patch("src.core.ai.health.OpenAIClient") as MockOpenAI, \
             patch("src.core.ai.health.GeminiClient") as MockGemini:
            
            # Setup OpenAI mock
            mock_openai = MockOpenAI.return_value
            mock_openai.generate = AsyncMock(return_value=openai_response)
            
            # Setup Gemini mock
            mock_gemini = MagicMock()
            mock_gemini.count_tokens = AsyncMock(return_value=4)
            mock_gemini.__aenter__ = AsyncMock(return_value=mock_gemini)
            mock_gemini.__aexit__ = AsyncMock(return_value=None)
            MockGemini.return_value = mock_gemini
            
            report = await check_ai_health(settings)
        
        assert report.all_ok is True
        assert len(report.healthy_providers) == 2
        assert len(report.unhealthy_providers) == 0
        assert "openai" in report.providers
        assert "gemini" in report.providers
    
    @pytest.mark.asyncio
    async def test_some_providers_unhealthy(self):
        """Test health check with some providers unhealthy"""
        settings = AISettings(
            OPENAI_API_KEY="openai-key",
            GEMINI_API_KEY=None  # Missing Gemini key
        )
        
        openai_response = AIResponse(
            text="pong",
            provider="openai",
            model="gpt-4o-mini",
            total_tokens=5
        )
        
        with patch("src.core.ai.health.OpenAIClient") as MockOpenAI:
            mock_openai = MockOpenAI.return_value
            mock_openai.generate = AsyncMock(return_value=openai_response)
            
            report = await check_ai_health(settings)
        
        assert report.all_ok is False
        assert "openai" in report.healthy_providers
        assert "gemini" in report.unhealthy_providers
        assert report.providers["gemini"].error == "GEMINI_API_KEY not set"
    
    @pytest.mark.asyncio
    async def test_all_providers_unhealthy(self):
        """Test health check with all providers unhealthy"""
        settings = AISettings(
            OPENAI_API_KEY=None,
            GEMINI_API_KEY=None
        )
        
        report = await check_ai_health(settings)
        
        assert report.all_ok is False
        assert len(report.healthy_providers) == 0
        assert len(report.unhealthy_providers) == 2
    
    @pytest.mark.asyncio
    async def test_uses_default_settings(self):
        """Test health check uses default settings if not provided"""
        with patch("src.core.ai.health.AISettings") as MockSettings:
            mock_settings = MagicMock()
            mock_settings.OPENAI_API_KEY = None
            mock_settings.GEMINI_API_KEY = None
            MockSettings.return_value = mock_settings
            
            report = await check_ai_health()
            
            # Should call AISettings() to get defaults
            assert report is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
