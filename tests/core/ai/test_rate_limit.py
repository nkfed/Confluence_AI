"""
Tests for Rate Limiting functionality.

Tests the SimpleRateLimiter and its integration with AI clients.
"""

import pytest
import time
from unittest.mock import MagicMock, AsyncMock, patch
from src.core.ai.rate_limit import RateLimitConfig, SimpleRateLimiter


class TestRateLimitConfig:
    """Tests for RateLimitConfig dataclass"""
    
    def test_default_config(self):
        """Test default configuration values"""
        config = RateLimitConfig()
        assert config.max_rpm == 5
        assert config.min_interval_sec == 0.2
    
    def test_custom_config(self):
        """Test custom configuration"""
        config = RateLimitConfig(max_rpm=10, min_interval_sec=0.5)
        assert config.max_rpm == 10
        assert config.min_interval_sec == 0.5


class TestSimpleRateLimiter:
    """Tests for SimpleRateLimiter"""
    
    def test_initialization(self):
        """Test rate limiter initialization"""
        config = RateLimitConfig(max_rpm=10, min_interval_sec=0.3)
        limiter = SimpleRateLimiter(config)
        
        assert limiter.config == config
        assert limiter._last_call_ts is None
        assert limiter._requests_in_window == 0
    
    def test_first_call_no_delay(self):
        """Test first call passes without delay"""
        config = RateLimitConfig(max_rpm=5, min_interval_sec=0.2)
        limiter = SimpleRateLimiter(config)
        
        start = time.time()
        limiter.before_call()
        elapsed = time.time() - start
        
        # Should be nearly instant (< 50ms)
        assert elapsed < 0.05
        assert limiter._requests_in_window == 1
    
    def test_min_interval_enforcement(self):
        """Test minimum interval between requests"""
        config = RateLimitConfig(max_rpm=100, min_interval_sec=0.1)
        limiter = SimpleRateLimiter(config)
        
        # First call
        limiter.before_call()
        
        # Second call immediately - should sleep
        start = time.time()
        limiter.before_call()
        elapsed = time.time() - start
        
        # Should have slept ~0.1 seconds
        assert elapsed >= 0.09  # Allow small margin
        assert limiter._requests_in_window == 2
    
    def test_rpm_limit_enforcement(self):
        """Test RPM limit enforcement"""
        config = RateLimitConfig(max_rpm=2, min_interval_sec=0.0)
        limiter = SimpleRateLimiter(config)
        
        # Make 2 requests (at limit)
        limiter.before_call()
        limiter.before_call()
        
        assert limiter._requests_in_window == 2
        
        # Third request should trigger window reset
        # We can't easily test the sleep without mocking,
        # but we can verify the window resets
        with patch('time.sleep') as mock_sleep:
            limiter.before_call()
            # Should have called sleep to wait for new window
            assert mock_sleep.called
    
    def test_window_reset_after_60_seconds(self):
        """Test that window resets after 60 seconds"""
        config = RateLimitConfig(max_rpm=5, min_interval_sec=0.0)
        limiter = SimpleRateLimiter(config)
        
        # Make some requests
        limiter.before_call()
        limiter.before_call()
        assert limiter._requests_in_window == 2
        
        # Simulate 60+ seconds passing
        limiter._window_start_ts = time.time() - 61
        
        # Next call should reset window
        limiter.before_call()
        
        # Window should be reset (request count starts at 1)
        assert limiter._requests_in_window == 1
    
    def test_get_stats(self):
        """Test getting rate limiter statistics"""
        config = RateLimitConfig(max_rpm=10, min_interval_sec=0.2)
        limiter = SimpleRateLimiter(config)
        
        # Before any calls
        stats = limiter.get_stats()
        assert stats["requests_in_window"] == 0
        assert stats["max_rpm"] == 10
        assert stats["can_make_request"] is True
        assert stats["last_call_ago_sec"] is None
        
        # After a call
        limiter.before_call()
        stats = limiter.get_stats()
        assert stats["requests_in_window"] == 1
        assert stats["can_make_request"] is True
        assert stats["last_call_ago_sec"] is not None
        assert stats["last_call_ago_sec"] < 1.0  # Very recent
    
    def test_multiple_rapid_calls_with_sleep_mock(self):
        """Test multiple rapid calls trigger appropriate sleeps"""
        config = RateLimitConfig(max_rpm=3, min_interval_sec=0.1)
        limiter = SimpleRateLimiter(config)
        
        with patch('time.sleep') as mock_sleep:
            # First call - no sleep
            limiter.before_call()
            assert mock_sleep.call_count == 0
            
            # Second call - min interval sleep
            limiter.before_call()
            assert mock_sleep.call_count >= 1
            
            # Third call - min interval sleep
            limiter.before_call()
            assert mock_sleep.call_count >= 2
            
            # Fourth call - exceeds RPM, should sleep until window reset
            limiter.before_call()
            assert mock_sleep.call_count >= 3


class TestRateLimiterIntegrationWithGemini:
    """Tests for rate limiter integration with GeminiClient"""
    
    @pytest.mark.asyncio
    async def test_gemini_with_rate_limiter(self):
        """Test that GeminiClient calls rate limiter before API requests"""
        from src.core.ai.gemini_client import GeminiClient
        
        config = RateLimitConfig(max_rpm=5, min_interval_sec=0.1)
        limiter = SimpleRateLimiter(config)
        
        # Mock the rate limiter to track calls
        limiter.before_call = MagicMock()
        
        client = GeminiClient(
            api_key="test-key",
            rate_limiter=limiter
        )
        
        # Mock HTTP client
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "candidates": [
                {"content": {"parts": [{"text": "response"}]}}
            ],
            "usageMetadata": {"totalTokenCount": 10}
        }
        
        with patch.object(client._client, 'post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            
            await client.generate("test prompt")
            
            # Rate limiter should have been called
            limiter.before_call.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_gemini_without_rate_limiter(self):
        """Test that GeminiClient works without rate limiter"""
        from src.core.ai.gemini_client import GeminiClient
        
        client = GeminiClient(
            api_key="test-key",
            rate_limiter=None
        )
        
        # Mock HTTP client
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "candidates": [
                {"content": {"parts": [{"text": "response"}]}}
            ],
            "usageMetadata": {"totalTokenCount": 10}
        }
        
        with patch.object(client._client, 'post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            
            # Should work without rate limiter
            result = await client.generate("test prompt")
            assert result.text == "response"
    
    @pytest.mark.asyncio
    async def test_gemini_count_tokens_with_rate_limiter(self):
        """Test that count_tokens also uses rate limiter"""
        from src.core.ai.gemini_client import GeminiClient
        
        config = RateLimitConfig(max_rpm=5, min_interval_sec=0.1)
        limiter = SimpleRateLimiter(config)
        limiter.before_call = MagicMock()
        
        client = GeminiClient(
            api_key="test-key",
            rate_limiter=limiter
        )
        
        # Mock HTTP client
        mock_response = MagicMock()
        mock_response.json.return_value = {"totalTokens": 10}
        
        with patch.object(client._client, 'post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            
            await client.count_tokens("test text")
            
            # Rate limiter should have been called
            limiter.before_call.assert_called_once()


class TestRateLimiterIntegrationWithOpenAI:
    """Tests for rate limiter integration with OpenAIClient"""
    
    @pytest.mark.asyncio
    async def test_openai_with_rate_limiter(self):
        """Test that OpenAIClient calls rate limiter before API requests"""
        from src.core.ai.openai_client import OpenAIClient
        
        config = RateLimitConfig(max_rpm=5, min_interval_sec=0.1)
        limiter = SimpleRateLimiter(config)
        limiter.before_call = MagicMock()
        
        client = OpenAIClient(
            api_key="test-key",
            rate_limiter=limiter
        )
        
        # Mock OpenAI client response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="response"))]
        mock_response.usage = MagicMock(
            prompt_tokens=5,
            completion_tokens=5,
            total_tokens=10
        )
        mock_response.model_dump = MagicMock(return_value={"id": "test"})
        
        with patch.object(client.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_response
            
            await client.generate("test prompt")
            
            # Rate limiter should have been called
            limiter.before_call.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_openai_without_rate_limiter(self):
        """Test that OpenAIClient works without rate limiter"""
        from src.core.ai.openai_client import OpenAIClient
        
        client = OpenAIClient(
            api_key="test-key",
            rate_limiter=None
        )
        
        # Mock OpenAI client response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="response"))]
        mock_response.usage = MagicMock(
            prompt_tokens=5,
            completion_tokens=5,
            total_tokens=10
        )
        mock_response.model_dump = MagicMock(return_value={"id": "test"})
        
        with patch.object(client.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_response
            
            # Should work without rate limiter
            result = await client.generate("test prompt")
            assert result.text == "response"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
