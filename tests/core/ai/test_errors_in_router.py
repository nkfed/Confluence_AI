"""
Tests for Error Handling in AI Provider Router.

Tests custom exceptions and fallback behavior.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from src.core.ai.router import AIProviderRouter
from src.core.ai.interface import AIResponse
from src.core.ai.errors import (
    ProviderUnavailableError,
    FallbackFailedError,
)


class TestProviderUnavailableError:
    """Tests for ProviderUnavailableError"""
    
    @pytest.mark.asyncio
    async def test_unknown_provider_raises_error(self):
        """Test that requesting unknown provider raises ProviderUnavailableError"""
        router = AIProviderRouter()
        
        with pytest.raises(ProviderUnavailableError, match="unknown-provider"):
            await router.generate("Hello", provider="unknown-provider")
    
    @pytest.mark.asyncio
    async def test_primary_fails_no_fallback(self):
        """Test that primary failure without fallback raises ProviderUnavailableError"""
        # Create mock client that fails
        mock_client = AsyncMock()
        mock_client.name = "openai"
        mock_client.generate = AsyncMock(side_effect=RuntimeError("API Error"))
        
        # Router without fallback
        router = AIProviderRouter(
            default_provider="openai",
            fallback_provider=None,
            providers={"openai": mock_client},
            auto_register=False
        )
        
        with pytest.raises(ProviderUnavailableError, match="Primary provider.*failed"):
            await router.generate("Hello")
    
    @pytest.mark.asyncio
    async def test_primary_fails_fallback_same_as_primary(self):
        """Test that when fallback is same as primary, no fallback attempt is made"""
        # Create mock client that fails
        mock_client = AsyncMock()
        mock_client.name = "openai"
        mock_client.generate = AsyncMock(side_effect=RuntimeError("API Error"))
        
        # Router with fallback same as primary
        router = AIProviderRouter(
            default_provider="openai",
            fallback_provider="openai",
            providers={"openai": mock_client},
            auto_register=False
        )
        
        with pytest.raises(ProviderUnavailableError, match="Primary provider.*failed"):
            await router.generate("Hello")
        
        # Verify generate was called only once (no fallback attempt)
        assert mock_client.generate.call_count == 1


class TestFallbackSuccess:
    """Tests for successful fallback scenarios"""
    
    @pytest.mark.asyncio
    async def test_primary_fails_fallback_succeeds(self):
        """Test that when primary fails, fallback is used successfully"""
        # Mock primary client (fails)
        mock_primary = AsyncMock()
        mock_primary.name = "openai"
        mock_primary.generate = AsyncMock(side_effect=RuntimeError("Primary error"))
        
        # Mock fallback client (succeeds)
        mock_fallback = AsyncMock()
        mock_fallback.name = "gemini"
        mock_fallback.generate = AsyncMock(return_value=AIResponse(
            text="Fallback response",
            provider="gemini",
            model="gemini-2.0-flash-exp",
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15
        ))
        
        # Router with fallback
        router = AIProviderRouter(
            default_provider="openai",
            fallback_provider="gemini",
            providers={"openai": mock_primary, "gemini": mock_fallback},
            auto_register=False
        )
        
        # Should succeed with fallback
        result = await router.generate("Hello")
        
        assert result.text == "Fallback response"
        assert result.provider == "gemini"
        
        # Verify both were called
        mock_primary.generate.assert_called_once()
        mock_fallback.generate.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_explicit_provider_fails_fallback_succeeds(self):
        """Test fallback when explicitly specifying primary provider"""
        # Mock clients
        mock_primary = AsyncMock()
        mock_primary.name = "openai"
        mock_primary.generate = AsyncMock(side_effect=RuntimeError("Primary error"))
        
        mock_fallback = AsyncMock()
        mock_fallback.name = "gemini"
        mock_fallback.generate = AsyncMock(return_value=AIResponse(
            text="Fallback response",
            provider="gemini",
            model="gemini-2.0-flash-exp",
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15
        ))
        
        # Router
        router = AIProviderRouter(
            default_provider="gemini",
            fallback_provider="gemini",
            providers={"openai": mock_primary, "gemini": mock_fallback},
            auto_register=False
        )
        
        # Explicitly request openai (which will fail)
        result = await router.generate("Hello", provider="openai")
        
        # Should fallback to gemini
        assert result.text == "Fallback response"
        assert result.provider == "gemini"


class TestFallbackFailedError:
    """Tests for FallbackFailedError scenarios"""
    
    @pytest.mark.asyncio
    async def test_both_providers_fail(self):
        """Test that when both primary and fallback fail, FallbackFailedError is raised"""
        # Mock primary client (fails)
        mock_primary = AsyncMock()
        mock_primary.name = "openai"
        mock_primary.generate = AsyncMock(side_effect=RuntimeError("Primary error"))
        
        # Mock fallback client (also fails)
        mock_fallback = AsyncMock()
        mock_fallback.name = "gemini"
        mock_fallback.generate = AsyncMock(side_effect=RuntimeError("Fallback error"))
        
        # Router with fallback
        router = AIProviderRouter(
            default_provider="openai",
            fallback_provider="gemini",
            providers={"openai": mock_primary, "gemini": mock_fallback},
            auto_register=False
        )
        
        # Should raise FallbackFailedError
        with pytest.raises(FallbackFailedError) as exc_info:
            await router.generate("Hello")
        
        # Verify error message contains both errors
        error_msg = str(exc_info.value)
        assert "Primary provider" in error_msg
        assert "Fallback provider" in error_msg
        assert "Primary error" in error_msg or "openai" in error_msg
        assert "Fallback error" in error_msg or "gemini" in error_msg
        
        # Verify both were called
        mock_primary.generate.assert_called_once()
        mock_fallback.generate.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_fallback_error_contains_both_exception_details(self):
        """Test that FallbackFailedError preserves details from both exceptions"""
        # Custom exceptions with specific messages
        class CustomPrimaryError(Exception):
            pass
        
        class CustomFallbackError(Exception):
            pass
        
        mock_primary = AsyncMock()
        mock_primary.name = "openai"
        mock_primary.generate = AsyncMock(
            side_effect=CustomPrimaryError("Rate limit exceeded")
        )
        
        mock_fallback = AsyncMock()
        mock_fallback.name = "gemini"
        mock_fallback.generate = AsyncMock(
            side_effect=CustomFallbackError("Service unavailable")
        )
        
        router = AIProviderRouter(
            default_provider="openai",
            fallback_provider="gemini",
            providers={"openai": mock_primary, "gemini": mock_fallback},
            auto_register=False
        )
        
        with pytest.raises(FallbackFailedError) as exc_info:
            await router.generate("Hello")
        
        error_msg = str(exc_info.value)
        assert "Rate limit exceeded" in error_msg
        assert "Service unavailable" in error_msg


class TestSuccessfulGeneration:
    """Tests for successful generation scenarios"""
    
    @pytest.mark.asyncio
    async def test_primary_succeeds_no_fallback_needed(self):
        """Test that when primary succeeds, fallback is not called"""
        # Mock primary client (succeeds)
        mock_primary = AsyncMock()
        mock_primary.name = "openai"
        mock_primary.generate = AsyncMock(return_value=AIResponse(
            text="Primary response",
            provider="openai",
            model="gpt-4o-mini",
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15
        ))
        
        # Mock fallback client (should not be called)
        mock_fallback = AsyncMock()
        mock_fallback.name = "gemini"
        mock_fallback.generate = AsyncMock()
        
        # Router with fallback
        router = AIProviderRouter(
            default_provider="openai",
            fallback_provider="gemini",
            providers={"openai": mock_primary, "gemini": mock_fallback},
            auto_register=False
        )
        
        # Should succeed with primary
        result = await router.generate("Hello")
        
        assert result.text == "Primary response"
        assert result.provider == "openai"
        
        # Verify only primary was called
        mock_primary.generate.assert_called_once()
        mock_fallback.generate.assert_not_called()


class TestErrorInheritance:
    """Tests for exception inheritance"""
    
    def test_all_errors_inherit_from_ai_provider_error(self):
        """Test that all custom errors inherit from AIProviderError"""
        from src.core.ai.errors import AIProviderError
        
        assert issubclass(ProviderUnavailableError, AIProviderError)
        assert issubclass(FallbackFailedError, AIProviderError)
    
    def test_can_catch_with_base_exception(self):
        """Test that all errors can be caught with base AIProviderError"""
        from src.core.ai.errors import AIProviderError
        
        try:
            raise ProviderUnavailableError("Test")
        except AIProviderError:
            pass  # Should catch
        
        try:
            raise FallbackFailedError("Test")
        except AIProviderError:
            pass  # Should catch


class TestErrorMessages:
    """Tests for error message content"""
    
    @pytest.mark.asyncio
    async def test_provider_unavailable_message_includes_provider_name(self):
        """Test that ProviderUnavailableError includes provider name"""
        router = AIProviderRouter()
        
        try:
            await router.generate("Hello", provider="unknown-provider")
        except ProviderUnavailableError as e:
            assert "unknown-provider" in str(e)
    
    @pytest.mark.asyncio
    async def test_fallback_failed_message_includes_both_providers(self):
        """Test that FallbackFailedError mentions both providers"""
        mock_primary = AsyncMock()
        mock_primary.name = "openai"
        mock_primary.generate = AsyncMock(side_effect=RuntimeError("Error 1"))
        
        mock_fallback = AsyncMock()
        mock_fallback.name = "gemini"
        mock_fallback.generate = AsyncMock(side_effect=RuntimeError("Error 2"))
        
        router = AIProviderRouter(
            default_provider="openai",
            fallback_provider="gemini",
            providers={"openai": mock_primary, "gemini": mock_fallback},
            auto_register=False
        )
        
        try:
            await router.generate("Hello")
        except FallbackFailedError as e:
            error_msg = str(e)
            assert "openai" in error_msg or "Primary" in error_msg
            assert "gemini" in error_msg or "Fallback" in error_msg


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
