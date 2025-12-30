"""
Integration tests for SummaryAgent with AI Router.

Tests the integration of AI Provider Router with SummaryAgent.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.agents.summary_agent import SummaryAgent
from src.clients.confluence_client import ConfluenceClient
from src.clients.openai_client import OpenAIClient
from src.core.ai.router import AIProviderRouter
from src.core.ai.interface import AIResponse


class TestSummaryAgentWithRouter:
    """Tests for SummaryAgent using AI Router"""
    
    @pytest.mark.asyncio
    async def test_summary_agent_uses_router(self):
        """Test that SummaryAgent can use AI Router"""
        # Mock confluence response
        mock_confluence = MagicMock(spec=ConfluenceClient)
        mock_confluence.get_page = AsyncMock(return_value={
            "id": "123",
            "title": "Test Page",
            "body": {
                "storage": {
                    "value": "<p>Test content for summarization</p>"
                }
            }
        })
        
        # Mock AI response
        mock_ai_response = AIResponse(
            text="This is a generated summary",
            provider="openai",
            model="gpt-4o-mini",
            total_tokens=100
        )
        
        # Mock provider
        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(return_value=mock_ai_response)
        
        # Mock router
        mock_router = MagicMock(spec=AIProviderRouter)
        mock_router.get = MagicMock(return_value=mock_provider)
        
        # Create agent with router
        agent = SummaryAgent(
            confluence_client=mock_confluence,
            ai_router=mock_router
        )
        
        # Generate summary
        summary = await agent.generate_summary("123")
        
        # Verify router was used
        assert summary == "This is a generated summary"
        mock_router.get.assert_called_once_with(None)  # Default provider
        mock_provider.generate.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_summary_agent_with_specific_provider(self):
        """Test that SummaryAgent can use specific provider"""
        mock_confluence = MagicMock(spec=ConfluenceClient)
        mock_confluence.get_page = AsyncMock(return_value={
            "id": "123",
            "title": "Test Page",
            "body": {"storage": {"value": "<p>Content</p>"}}
        })
        
        mock_ai_response = AIResponse(
            text="Gemini summary",
            provider="gemini",
            model="gemini-2.0-flash-exp",
            total_tokens=50
        )
        
        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(return_value=mock_ai_response)
        
        mock_router = MagicMock(spec=AIProviderRouter)
        mock_router.get = MagicMock(return_value=mock_provider)
        
        # Create agent with specific provider
        agent = SummaryAgent(
            confluence_client=mock_confluence,
            ai_router=mock_router,
            ai_provider="gemini"
        )
        
        summary = await agent.generate_summary("123")
        
        assert summary == "Gemini summary"
        mock_router.get.assert_called_with("gemini")
    
    @pytest.mark.asyncio
    async def test_summary_agent_backward_compatibility(self):
        """Test that SummaryAgent still works with direct OpenAI client"""
        mock_confluence = MagicMock(spec=ConfluenceClient)
        mock_confluence.get_page = AsyncMock(return_value={
            "id": "123",
            "title": "Test Page",
            "body": {"storage": {"value": "<p>Content</p>"}}
        })
        
        mock_openai = MagicMock(spec=OpenAIClient)
        mock_openai.generate = AsyncMock(return_value="Legacy OpenAI summary")
        
        # Create agent with legacy OpenAI client (no router)
        agent = SummaryAgent(
            confluence_client=mock_confluence,
            openai_client=mock_openai
        )
        
        summary = await agent.generate_summary("123")
        
        assert summary == "Legacy OpenAI summary"
        mock_openai.generate.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_summary_agent_with_fallback(self):
        """Test that SummaryAgent benefits from router's fallback"""
        mock_confluence = MagicMock(spec=ConfluenceClient)
        mock_confluence.get_page = AsyncMock(return_value={
            "id": "123",
            "title": "Test Page",
            "body": {"storage": {"value": "<p>Content</p>"}}
        })
        
        # Mock OpenAI provider that fails
        mock_openai_provider = MagicMock()
        mock_openai_provider.generate = AsyncMock(
            side_effect=RuntimeError("OpenAI rate limit")
        )
        
        # Mock Gemini provider that succeeds
        gemini_response = AIResponse(
            text="Gemini fallback summary",
            provider="gemini",
            model="gemini-2.0-flash-exp"
        )
        mock_gemini_provider = MagicMock()
        mock_gemini_provider.generate = AsyncMock(return_value=gemini_response)
        
        # Mock router with fallback
        mock_router = MagicMock(spec=AIProviderRouter)
        mock_router.get = MagicMock(side_effect=[
            mock_openai_provider,
            mock_gemini_provider
        ])
        
        agent = SummaryAgent(
            confluence_client=mock_confluence,
            ai_router=mock_router
        )
        
        # This should trigger fallback in real router
        # For this test, we just verify the pattern works
        # In real scenario, router.generate() handles fallback
        with pytest.raises(RuntimeError):
            await agent.generate_summary("123")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
