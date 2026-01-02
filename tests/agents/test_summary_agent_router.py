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
from types import SimpleNamespace


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
            text="TEST_RESPONSE",
            provider="mock",
            model="mock-model",
            total_tokens=0
        )
        
        # Mock provider
        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(return_value=mock_ai_response)
        
        # Mock router with proper async generate method
        mock_router = MagicMock(spec=AIProviderRouter)
        mock_router.get = MagicMock(return_value=mock_provider)
        mock_router.generate = AsyncMock(return_value=mock_ai_response)
        
        # Create agent with router
        agent = SummaryAgent(
            confluence_client=mock_confluence,
            ai_router=mock_router
        )
        
        # Generate summary
        summary = await agent.generate_summary("123")
        
        # Verify router was used
        assert summary == "TEST_RESPONSE"
        mock_router.generate.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_summary_agent_with_specific_provider(self):
        """Test that SummaryAgent can use specific provider"""
        mock_confluence = MagicMock(spec=ConfluenceClient)
        mock_confluence.get_page = AsyncMock(return_value={
            "id": "123",
            "title": "Test Page",
            "body": {"storage": {"value": "<p>Content</p>"}}
        })
        
        # Ensure mock AI response includes all required fields
        mock_ai_response = AIResponse(
            text="TEST_RESPONSE",
            provider="gemini",
            model="gemini-2.0-flash-exp",
            prompt_tokens=20,
            completion_tokens=30,
            total_tokens=50
        )
        
        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(return_value=mock_ai_response)
        
        mock_router = MagicMock(spec=AIProviderRouter)
        mock_router.get = MagicMock(return_value=mock_provider)
        mock_router.generate = AsyncMock(return_value=mock_ai_response)
        
        # Create agent with specific provider
        agent = SummaryAgent(
            confluence_client=mock_confluence,
            ai_router=mock_router,
            ai_provider="gemini"
        )
        
        summary = await agent.generate_summary("123")
        
        assert summary == "TEST_RESPONSE"
        mock_router.generate.assert_called_once()
    
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
        
        # Mock fallback response from router
        gemini_response = AIResponse(
            text="TEST_RESPONSE",
            provider="gemini",
            model="gemini-2.0-flash-exp",
            total_tokens=0
        )
        
        # Mock router that handles fallback internally
        mock_router = MagicMock(spec=AIProviderRouter)
        mock_router.generate = AsyncMock(return_value=gemini_response)
        
        agent = SummaryAgent(
            confluence_client=mock_confluence,
            ai_router=mock_router
        )
        
        # Router handles fallback internally, agent just gets result
        summary = await agent.generate_summary("123")
        assert summary == "TEST_RESPONSE"
        mock_router.generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_summary_agent_mock_response(self):
        """Test that SummaryAgent works with mocked AI response"""
        mock_confluence = MagicMock(spec=ConfluenceClient)
        mock_confluence.get_page = AsyncMock(return_value={
            "id": "123",
            "title": "Test Page",
            "body": {"storage": {"value": "<p>Content</p>"}}
        })
        
        # Create AIResponse for consistency
        mock_ai_response = AIResponse(
            text="TEST_RESPONSE",
            provider="mock",
            model="mock-model",
            total_tokens=0
        )

        # Mock router
        mock_router = MagicMock(spec=AIProviderRouter)
        mock_router.generate = AsyncMock(return_value=mock_ai_response)
        
        # Create agent with router
        agent = SummaryAgent(
            confluence_client=mock_confluence,
            ai_router=mock_router
        )
        
        # Generate summary
        summary = await agent.generate_summary("123")
        
        # Ensure the test validates against the expected response
        assert summary == "TEST_RESPONSE"
        mock_router.generate.assert_called_once()
        


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
