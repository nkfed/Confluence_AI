"""
Tests for Unified Logging Layer.

Tests the log_ai_call function and its integration with agents.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.core.ai.logging_utils import log_ai_call
from src.core.ai.interface import AIResponse


class TestLogAICallSuccess:
    """Tests for successful AI calls"""
    
    @pytest.mark.asyncio
    async def test_log_ai_call_executes_coro(self):
        """Test that log_ai_call executes the provided coroutine"""
        mock_result = AIResponse(
            text="test response",
            provider="openai",
            model="gpt-4o-mini",
            prompt_tokens=10,
            completion_tokens=20,
            total_tokens=30
        )
        
        async def mock_coro():
            return mock_result
        
        result = await log_ai_call(
            provider_name="openai",
            model="gpt-4o-mini",
            operation="test",
            coro=mock_coro
        )
        
        assert result == mock_result
    
    @pytest.mark.asyncio
    async def test_log_ai_call_logs_success(self, caplog):
        """Test that successful call is logged with correct information"""
        mock_result = AIResponse(
            text="test response",
            provider="openai",
            model="gpt-4o-mini",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150
        )
        
        async def mock_coro():
            return mock_result
        
        with caplog.at_level("INFO"):
            await log_ai_call(
                provider_name="openai",
                model="gpt-4o-mini",
                operation="summary",
                coro=mock_coro
            )
        
        # Check that success was logged
        assert "AI call succeeded" in caplog.text
    
    @pytest.mark.asyncio
    async def test_log_ai_call_includes_provider_and_model(self):
        """Test that provider and model are included in logs"""
        mock_result = AIResponse(
            text="test",
            provider="gemini",
            model="gemini-2.0-flash-exp",
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15
        )
        
        async def mock_coro():
            return mock_result
        
        with patch("src.core.ai.logging_utils.logger") as mock_logger:
            await log_ai_call(
                provider_name="gemini",
                model="gemini-2.0-flash-exp",
                operation="tagging",
                coro=mock_coro
            )
            
            # Verify logger.info was called
            mock_logger.info.assert_called_once()
            
            # Get the call arguments
            args, kwargs = mock_logger.info.call_args
            
            # Check message
            assert args[0] == "AI call succeeded"
            
            # Check extra data
            extra = kwargs.get("extra", {})
            assert extra["provider"] == "gemini"
            assert extra["model"] == "gemini-2.0-flash-exp"
            assert extra["operation"] == "tagging"
    
    @pytest.mark.asyncio
    async def test_log_ai_call_includes_duration(self):
        """Test that execution duration is logged"""
        mock_result = AIResponse(
            text="test",
            provider="openai",
            model="gpt-4o-mini",
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15
        )
        
        async def mock_coro():
            return mock_result
        
        with patch("src.core.ai.logging_utils.logger") as mock_logger:
            await log_ai_call(
                provider_name="openai",
                model="gpt-4o-mini",
                operation="test",
                coro=mock_coro
            )
            
            args, kwargs = mock_logger.info.call_args
            extra = kwargs.get("extra", {})
            
            # Duration should be present and be a number
            assert "duration_sec" in extra
            assert isinstance(extra["duration_sec"], (int, float))
            assert extra["duration_sec"] >= 0
    
    @pytest.mark.asyncio
    async def test_log_ai_call_includes_tokens(self):
        """Test that token counts are logged"""
        mock_result = AIResponse(
            text="test",
            provider="openai",
            model="gpt-4o-mini",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150
        )
        
        async def mock_coro():
            return mock_result
        
        with patch("src.core.ai.logging_utils.logger") as mock_logger:
            await log_ai_call(
                provider_name="openai",
                model="gpt-4o-mini",
                operation="test",
                coro=mock_coro
            )
            
            args, kwargs = mock_logger.info.call_args
            extra = kwargs.get("extra", {})
            
            # Token counts should be present
            assert extra["prompt_tokens"] == 100
            assert extra["completion_tokens"] == 50
            assert extra["total_tokens"] == 150
    
    @pytest.mark.asyncio
    async def test_log_ai_call_includes_cost(self):
        """Test that cost estimate is logged"""
        mock_result = AIResponse(
            text="test",
            provider="openai",
            model="gpt-4o-mini",
            prompt_tokens=1000,
            completion_tokens=500,
            total_tokens=1500
        )
        
        async def mock_coro():
            return mock_result
        
        with patch("src.core.ai.logging_utils.logger") as mock_logger:
            await log_ai_call(
                provider_name="openai",
                model="gpt-4o-mini",
                operation="test",
                coro=mock_coro
            )
            
            args, kwargs = mock_logger.info.call_args
            extra = kwargs.get("extra", {})
            
            # Cost should be present and be a number
            assert "cost_usd" in extra
            assert isinstance(extra["cost_usd"], (int, float))
            assert extra["cost_usd"] > 0


class TestLogAICallError:
    """Tests for AI calls that fail"""
    
    @pytest.mark.asyncio
    async def test_log_ai_call_logs_error(self):
        """Test that errors are logged"""
        error_message = "API rate limit exceeded"
        
        async def failing_coro():
            raise RuntimeError(error_message)
        
        with patch("src.core.ai.logging_utils.logger") as mock_logger:
            with pytest.raises(RuntimeError):
                await log_ai_call(
                    provider_name="openai",
                    model="gpt-4o-mini",
                    operation="test",
                    coro=failing_coro
                )
            
            # Verify error was logged
            mock_logger.error.assert_called_once()
            
            args, kwargs = mock_logger.error.call_args
            assert args[0] == "AI call failed"
            
            extra = kwargs.get("extra", {})
            assert extra["error"] == error_message
    
    @pytest.mark.asyncio
    async def test_log_ai_call_includes_error_type(self):
        """Test that error type is logged"""
        async def failing_coro():
            raise ValueError("Invalid input")
        
        with patch("src.core.ai.logging_utils.logger") as mock_logger:
            with pytest.raises(ValueError):
                await log_ai_call(
                    provider_name="openai",
                    model="gpt-4o-mini",
                    operation="test",
                    coro=failing_coro
                )
            
            args, kwargs = mock_logger.error.call_args
            extra = kwargs.get("extra", {})
            
            assert extra["error_type"] == "ValueError"
    
    @pytest.mark.asyncio
    async def test_log_ai_call_reraises_exception(self):
        """Test that exceptions are re-raised after logging"""
        async def failing_coro():
            raise RuntimeError("Test error")
        
        with pytest.raises(RuntimeError, match="Test error"):
            await log_ai_call(
                provider_name="openai",
                model="gpt-4o-mini",
                operation="test",
                coro=failing_coro
            )
    
    @pytest.mark.asyncio
    async def test_log_ai_call_includes_duration_on_error(self):
        """Test that duration is logged even on error"""
        async def failing_coro():
            raise RuntimeError("Test error")
        
        with patch("src.core.ai.logging_utils.logger") as mock_logger:
            with pytest.raises(RuntimeError):
                await log_ai_call(
                    provider_name="openai",
                    model="gpt-4o-mini",
                    operation="test",
                    coro=failing_coro
                )
            
            args, kwargs = mock_logger.error.call_args
            extra = kwargs.get("extra", {})
            
            # Duration should be present even on error
            assert "duration_sec" in extra
            assert isinstance(extra["duration_sec"], (int, float))


class TestLogAICallWithoutTokens:
    """Tests for calls that don't return token information"""
    
    @pytest.mark.asyncio
    async def test_log_ai_call_handles_missing_tokens(self):
        """Test that calls without token info are handled gracefully"""
        # Result without token attributes (simple object without __format__)
        class SimpleResult:
            def __init__(self):
                self.text = "test response"
        
        mock_result = SimpleResult()
        
        async def mock_coro():
            return mock_result
        
        with patch("src.core.ai.logging_utils.logger") as mock_logger:
            result = await log_ai_call(
                provider_name="openai",
                model="gpt-4o-mini",
                operation="test",
                coro=mock_coro
            )
            
            # Should still succeed
            assert result == mock_result
            
            # Check logged data
            args, kwargs = mock_logger.info.call_args
            extra = kwargs.get("extra", {})
            
            # Should not have token fields
            assert "prompt_tokens" not in extra
            assert "completion_tokens" not in extra
            assert "total_tokens" not in extra
            
            # Cost should be None
            assert extra["cost_usd"] is None


class TestLogAICallIntegration:
    """Integration tests with actual agents"""
    
    @pytest.mark.asyncio
    async def test_summary_agent_uses_log_ai_call(self):
        """Test that SummaryAgent uses unified logging"""
        from src.agents.summary_agent import SummaryAgent
        from src.core.ai.router import AIProviderRouter
        from src.core.ai.openai_client import OpenAIClient
        
        # Mock OpenAI client
        mock_client = AsyncMock(spec=OpenAIClient)
        mock_client.name = "openai"
        mock_client.model_default = "gpt-4o-mini"
        mock_client.generate = AsyncMock(return_value=AIResponse(
            text="Test summary",
            provider="openai",
            model="gpt-4o-mini",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150
        ))
        
        # Mock router
        router = AIProviderRouter(providers={"openai": mock_client})
        
        # Mock Confluence client
        with patch("src.agents.summary_agent.ConfluenceClient") as MockConfluence:
            mock_confluence = MockConfluence.return_value
            mock_confluence.get_page = AsyncMock(return_value={
                "title": "Test Page",
                "body": {"storage": {"value": "<p>Test content</p>"}}
            })
            
            # Create agent
            agent = SummaryAgent(
                confluence_client=mock_confluence,
                ai_router=router,
                ai_provider="openai"
            )
            
            # Mock log_ai_call to verify it's called
            with patch("src.agents.summary_agent.log_ai_call", wraps=log_ai_call) as mock_log:
                summary = await agent.generate_summary("12345")
                
                # Verify log_ai_call was used
                mock_log.assert_called_once()
                
                # Verify arguments
                call_args = mock_log.call_args
                assert call_args.kwargs["provider_name"] == "openai"
                assert call_args.kwargs["model"] == "gpt-4o-mini"
                assert call_args.kwargs["operation"] == "summary"
    
    @pytest.mark.asyncio
    async def test_tagging_agent_uses_log_ai_call(self):
        """Test that TaggingAgent uses unified logging"""
        from src.agents.tagging_agent import TaggingAgent
        from src.core.ai.router import AIProviderRouter
        from src.core.ai.gemini_client import GeminiClient
        
        # Mock Gemini client
        mock_client = AsyncMock(spec=GeminiClient)
        mock_client.name = "gemini"
        mock_client.model_default = "gemini-2.0-flash-exp"
        mock_client.generate = AsyncMock(return_value=AIResponse(
            text='{"doc": [], "domain": [], "kb": [], "tool": []}',
            provider="gemini",
            model="gemini-2.0-flash-exp",
            prompt_tokens=50,
            completion_tokens=10,
            total_tokens=60
        ))
        
        # Mock router
        router = AIProviderRouter(providers={"gemini": mock_client})
        
        # Create agent
        agent = TaggingAgent(
            ai_router=router,
            ai_provider="gemini"
        )
        
        # Mock log_ai_call to verify it's called
        with patch("src.agents.tagging_agent.log_ai_call", wraps=log_ai_call) as mock_log:
            tags = await agent.suggest_tags("Test content")
            
            # Verify log_ai_call was used
            mock_log.assert_called_once()
            
            # Verify arguments
            call_args = mock_log.call_args
            assert call_args.kwargs["provider_name"] == "gemini"
            assert call_args.kwargs["model"] == "gemini-2.0-flash-exp"
            assert call_args.kwargs["operation"] == "tagging"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
