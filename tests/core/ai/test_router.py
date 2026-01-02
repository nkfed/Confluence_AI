"""
Tests for AI Provider Router.

This module tests the central router for managing AI providers.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.core.ai.router import AIProviderRouter
from src.core.ai.interface import AIResponse
from src.core.ai.errors import ProviderUnavailableError, FallbackFailedError


class TestAIProviderRouterInitialization:
    """Tests for router initialization"""
    
    def test_init_default_provider(self):
        """Test initialization with default provider"""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            router = AIProviderRouter()
            assert router.default_provider == "openai"
            assert router.fallback_provider is None
    
    def test_init_custom_default(self):
        """Test initialization with custom default provider"""
        with patch.dict('os.environ', {'GEMINI_API_KEY': 'test-key'}):
            router = AIProviderRouter(default_provider="gemini")
            assert router.default_provider == "gemini"
    
    def test_init_with_fallback(self):
        """Test initialization with fallback provider"""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test', 'GEMINI_API_KEY': 'test'}):
            router = AIProviderRouter(
                default_provider="openai",
                fallback_provider="gemini"
            )
            assert router.default_provider == "openai"
            assert router.fallback_provider == "gemini"
    
    def test_auto_register_providers(self):
        """Test that providers are auto-registered"""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test', 'GEMINI_API_KEY': 'test'}):
            router = AIProviderRouter()
            
            # Check that providers were registered
            assert "openai" in router.providers
            assert "gemini" in router.providers
    
    def test_no_auto_register(self):
        """Test disabling auto-registration"""
        router = AIProviderRouter(auto_register=False)
        assert len(router.providers) == 0
    
    def test_init_with_pre_initialized_providers(self):
        """Test initialization with pre-initialized providers"""
        mock_provider = MagicMock()
        mock_provider.name = "custom"
        
        providers = {"custom": mock_provider}
        router = AIProviderRouter(providers=providers, auto_register=False)
        
        assert "custom" in router.providers
        assert router.get("custom") == mock_provider


class TestAIProviderRouterGetMethod:
    """Tests for get() method"""
    
    def test_get_default_provider(self):
        """Test getting default provider"""
        mock_openai = MagicMock()
        mock_openai.name = "openai"
        
        router = AIProviderRouter(
            providers={"openai": mock_openai},
            auto_register=False
        )
        
        provider = router.get()
        assert provider == mock_openai
    
    def test_get_specific_provider(self):
        """Test getting specific provider by name"""
        mock_openai = MagicMock()
        mock_gemini = MagicMock()
        
        router = AIProviderRouter(
            providers={"openai": mock_openai, "gemini": mock_gemini},
            auto_register=False
        )
        
        assert router.get("openai") == mock_openai
        assert router.get("gemini") == mock_gemini
    
    def test_get_unknown_provider_raises_error(self):
        """Test that getting unknown provider raises ValueError"""
        router = AIProviderRouter(auto_register=False)
        
        with pytest.raises(ValueError, match="AI provider 'unknown' is not configured"):
            router.get("unknown")
    
    def test_get_error_message_shows_available(self):
        """Test that error message shows available providers"""
        mock_provider = MagicMock()
        router = AIProviderRouter(
            providers={"test": mock_provider},
            auto_register=False
        )
        
        with pytest.raises(ValueError, match="Available providers: test"):
            router.get("unknown")


class TestAIProviderRouterGenerate:
    """Tests for generate() method"""
    
    @pytest.mark.asyncio
    async def test_generate_with_default_provider(self):
        """Test generation using default provider"""
        mock_response = AIResponse(
            text="Generated text",
            provider="openai",
            model="gpt-4o-mini"
        )
        
        mock_openai = MagicMock()
        mock_openai.generate = AsyncMock(return_value=mock_response)
        
        router = AIProviderRouter(
            providers={"openai": mock_openai},
            auto_register=False
        )
        
        result = await router.generate("Test prompt")
        
        assert result == mock_response
        mock_openai.generate.assert_called_once_with("Test prompt")
    
    @pytest.mark.asyncio
    async def test_generate_with_specific_provider(self):
        """Test generation with explicitly specified provider"""
        mock_response = AIResponse(
            text="Gemini response",
            provider="gemini",
            model="gemini-2.0-flash-exp"
        )
        
        mock_gemini = MagicMock()
        mock_gemini.generate = AsyncMock(return_value=mock_response)
        
        router = AIProviderRouter(
            default_provider="openai",
            providers={"gemini": mock_gemini},
            auto_register=False
        )
        
        result = await router.generate("Test prompt", provider="gemini")
        
        assert result == mock_response
        mock_gemini.generate.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_generate_with_kwargs(self):
        """Test that kwargs are passed to provider"""
        mock_response = AIResponse(
            text="Response",
            provider="openai",
            model="gpt-4o-mini"
        )
        
        mock_openai = MagicMock()
        mock_openai.generate = AsyncMock(return_value=mock_response)
        
        router = AIProviderRouter(
            providers={"openai": mock_openai},
            auto_register=False
        )
        
        await router.generate(
            "Test prompt",
            temperature=0.8,
            max_tokens=500
        )
        
        mock_openai.generate.assert_called_once_with(
            "Test prompt",
            temperature=0.8,
            max_tokens=500
        )
    
    @pytest.mark.asyncio
    async def test_generate_fallback_on_error(self):
        """Test fallback to secondary provider on error"""
        mock_openai = MagicMock()
        mock_openai.generate = AsyncMock(side_effect=RuntimeError("OpenAI failed"))
        
        fallback_response = AIResponse(
            text="Fallback response",
            provider="gemini",
            model="gemini-2.0-flash-exp"
        )
        mock_gemini = MagicMock()
        mock_gemini.generate = AsyncMock(return_value=fallback_response)
        
        router = AIProviderRouter(
            default_provider="openai",
            fallback_provider="gemini",
            providers={"openai": mock_openai, "gemini": mock_gemini},
            auto_register=False
        )
        
        result = await router.generate("Test prompt")
        
        # Should use fallback
        assert result == fallback_response
        mock_openai.generate.assert_called_once()
        mock_gemini.generate.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_generate_no_fallback_raises_error(self):
        """Test that error is raised if no fallback configured"""
        mock_openai = MagicMock()
        mock_openai.generate = AsyncMock(side_effect=RuntimeError("OpenAI failed"))
        
        router = AIProviderRouter(
            providers={"openai": mock_openai},
            auto_register=False
        )
        
        with pytest.raises(ProviderUnavailableError):
            await router.generate("Test prompt")
    
    @pytest.mark.asyncio
    async def test_generate_fallback_also_fails(self):
        """Test that error is raised if both providers fail"""
        mock_openai = MagicMock()
        mock_openai.generate = AsyncMock(side_effect=RuntimeError("OpenAI failed"))
        
        mock_gemini = MagicMock()
        mock_gemini.generate = AsyncMock(side_effect=RuntimeError("Gemini failed"))
        
        router = AIProviderRouter(
            default_provider="openai",
            fallback_provider="gemini",
            providers={"openai": mock_openai, "gemini": mock_gemini},
            auto_register=False
        )
        
        with pytest.raises(FallbackFailedError):
            await router.generate("Test prompt")
    
    @pytest.mark.asyncio
    async def test_generate_no_fallback_to_self(self):
        """Test that fallback doesn't use same provider"""
        call_count = 0
        
        async def mock_generate(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("First call failed")
            return AIResponse(text="Success", provider="openai", model="gpt-4o-mini")
        
        mock_openai = MagicMock()
        mock_openai.generate = mock_generate
        
        router = AIProviderRouter(
            default_provider="openai",
            fallback_provider="openai",  # Fallback to same provider
            providers={"openai": mock_openai},
            auto_register=False
        )
        
        # Should not retry with same provider; raises ProviderUnavailableError
        with pytest.raises(ProviderUnavailableError):
            await router.generate("Test prompt")
        
        assert call_count == 1


class TestAIProviderRouterCountTokens:
    """Tests for count_tokens() method"""
    
    @pytest.mark.asyncio
    async def test_count_tokens_default_provider(self):
        """Test token counting with default provider"""
        mock_gemini = MagicMock()
        mock_gemini.count_tokens = AsyncMock(return_value=42)
        
        router = AIProviderRouter(
            default_provider="gemini",
            providers={"gemini": mock_gemini},
            auto_register=False
        )
        
        result = await router.count_tokens("Test text")
        
        assert result == 42
        mock_gemini.count_tokens.assert_called_once_with("Test text")
    
    @pytest.mark.asyncio
    async def test_count_tokens_specific_provider(self):
        """Test token counting with specific provider"""
        mock_gemini = MagicMock()
        mock_gemini.count_tokens = AsyncMock(return_value=15)
        
        router = AIProviderRouter(
            providers={"gemini": mock_gemini},
            auto_register=False
        )
        
        result = await router.count_tokens("Test", provider="gemini")
        
        assert result == 15


class TestAIProviderRouterProperties:
    """Tests for router properties"""
    
    def test_providers_property(self):
        """Test providers property returns dict of registered providers"""
        mock_openai = MagicMock()
        mock_gemini = MagicMock()
        
        router = AIProviderRouter(
            providers={"openai": mock_openai, "gemini": mock_gemini},
            auto_register=False
        )
        
        providers = router.providers
        
        assert isinstance(providers, dict)
        assert "openai" in providers
        assert "gemini" in providers
    
    def test_default_provider_property(self):
        """Test default_provider property"""
        router = AIProviderRouter(default_provider="gemini", auto_register=False)
        assert router.default_provider == "gemini"
    
    def test_fallback_provider_property(self):
        """Test fallback_provider property"""
        router = AIProviderRouter(
            fallback_provider="gemini",
            auto_register=False
        )
        assert router.fallback_provider == "gemini"
    
    def test_has_provider(self):
        """Test has_provider method"""
        mock_provider = MagicMock()
        router = AIProviderRouter(
            providers={"test": mock_provider},
            auto_register=False
        )
        
        assert router.has_provider("test") is True
        assert router.has_provider("unknown") is False


class TestAIProviderRouterManualRegistration:
    """Tests for manual provider registration"""
    
    def test_register_provider(self):
        """Test manually registering a provider"""
        router = AIProviderRouter(auto_register=False)
        
        mock_provider = MagicMock()
        mock_provider.name = "custom"
        
        router.register("custom", mock_provider)
        
        assert router.has_provider("custom")
        assert router.get("custom") == mock_provider
    
    def test_register_overwrite_existing(self):
        """Test that manual registration can overwrite existing"""
        mock_old = MagicMock()
        mock_new = MagicMock()
        
        router = AIProviderRouter(
            providers={"test": mock_old},
            auto_register=False
        )
        
        router.register("test", mock_new)
        
        assert router.get("test") == mock_new


class TestAIProviderRouterIntegration:
    """Integration tests with real provider behavior simulation"""
    
    @pytest.mark.asyncio
    async def test_realistic_workflow(self):
        """Test realistic workflow with multiple providers"""
        # Mock OpenAI
        openai_response = AIResponse(
            text="OpenAI response",
            provider="openai",
            model="gpt-4o-mini",
            total_tokens=100
        )
        mock_openai = MagicMock()
        mock_openai.generate = AsyncMock(return_value=openai_response)
        
        # Mock Gemini
        gemini_response = AIResponse(
            text="Gemini response",
            provider="gemini",
            model="gemini-2.0-flash-exp",
            total_tokens=80
        )
        mock_gemini = MagicMock()
        mock_gemini.generate = AsyncMock(return_value=gemini_response)
        mock_gemini.count_tokens = AsyncMock(return_value=20)
        
        # Create router with fallback
        router = AIProviderRouter(
            default_provider="openai",
            fallback_provider="gemini",
            providers={"openai": mock_openai, "gemini": mock_gemini},
            auto_register=False
        )
        
        # Test default provider
        result1 = await router.generate("Test 1")
        assert result1.provider == "openai"
        
        # Test explicit provider
        result2 = await router.generate("Test 2", provider="gemini")
        assert result2.provider == "gemini"
        
        # Test token counting
        tokens = await router.count_tokens("Text", provider="gemini")
        assert tokens == 20


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
