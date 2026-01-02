"""
Integration tests for TaggingAgent with AI Router.

Tests the integration of AI Provider Router with TaggingAgent.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, ANY
from src.agents.tagging_agent import TaggingAgent
from src.clients.openai_client import OpenAIClient
from src.core.ai.router import AIProviderRouter
from src.core.ai.interface import AIResponse
from types import SimpleNamespace


class TestTaggingAgentWithRouter:
    """Tests for TaggingAgent using AI Router"""
    
    @pytest.mark.asyncio
    async def test_tagging_agent_uses_router(self):
        """Test that TaggingAgent can use AI Router"""
        # Mock AI response with tags
        mock_ai_response = AIResponse(
            text='{"doc": ["doc-tech"], "domain": [], "kb": [], "tool": ["tool-github-copilot"]}',
            provider="openai",
            model="gpt-4o-mini",
            total_tokens=150
        )
        
        # Mock router.generate
        mock_router = MagicMock(spec=AIProviderRouter)
        mock_router.generate = AsyncMock(return_value=mock_ai_response)
        
        # Create agent with router
        agent = TaggingAgent(ai_router=mock_router)
        
        # Suggest tags
        tags = await agent.suggest_tags("This is a technical document about GitHub Copilot")
        
        # Verify router was used
        assert tags["doc"] == ["doc-tech"]
        assert tags["tool"] == ["tool-github-copilot"]
        mock_router.generate.assert_awaited_once()
    
    @pytest.mark.asyncio
    async def test_tagging_agent_with_specific_provider(self):
        """Test that TaggingAgent can use specific provider"""
        mock_ai_response = AIResponse(
            text='{"doc": ["doc-business"], "domain": ["domain-ehealth-core"], "kb": [], "tool": []}',
            provider="gemini",
            model="gemini-2.0-flash-exp",
            total_tokens=80
        )
        
        mock_router = MagicMock(spec=AIProviderRouter)
        mock_router.generate = AsyncMock(return_value=mock_ai_response)
        
        # Create agent with specific provider
        agent = TaggingAgent(
            ai_router=mock_router,
            ai_provider="gemini"
        )
        
        tags = await agent.suggest_tags("Business document about eHealth")
        
        assert tags["doc"] == ["doc-business"]
        assert tags["domain"] == ["domain-ehealth-core"]
        mock_router.generate.assert_awaited_once_with(prompt=ANY, provider="gemini")
    
    @pytest.mark.asyncio
    async def test_tagging_agent_backward_compatibility(self):
        """Test that TaggingAgent still works with direct OpenAI client"""
        mock_openai = MagicMock(spec=OpenAIClient)
        mock_openai.generate = AsyncMock(
            return_value='{"doc": ["doc-tech"], "domain": [], "kb": [], "tool": []}'
        )
        
        # Create agent with legacy OpenAI client (no router)
        agent = TaggingAgent(openai_client=mock_openai)
        
        tags = await agent.suggest_tags("Technical documentation")
        
        assert tags["doc"] == ["doc-tech"]
        mock_openai.generate.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_tagging_agent_handles_invalid_json(self):
        """Test that TaggingAgent handles invalid JSON responses"""
        mock_ai_response = AIResponse(
            text="This is not valid JSON",
            provider="openai",
            model="gpt-4o-mini"
        )
        
        mock_router = MagicMock(spec=AIProviderRouter)
        mock_router.generate = AsyncMock(return_value=mock_ai_response)
        
        agent = TaggingAgent(ai_router=mock_router)
        
        tags = await agent.suggest_tags("Some text")
        
        # Should return empty structure when parsing fails
        assert "doc" in tags
        assert "domain" in tags
        assert "kb" in tags
        assert "tool" in tags
        mock_router.generate.assert_awaited_once()
    
    @pytest.mark.asyncio
    async def test_tagging_agent_with_multiple_providers(self):
        """Test switching between providers"""
        # OpenAI response
        openai_response = AIResponse(
            text='{"doc": ["doc-tech"], "domain": [], "kb": [], "tool": []}',
            provider="openai",
            model="gpt-4o-mini"
        )
        
        # Gemini response
        gemini_response = AIResponse(
            text='{"doc": ["doc-business"], "domain": [], "kb": [], "tool": []}',
            provider="gemini",
            model="gemini-2.0-flash-exp"
        )
        
        # Mock router.generate with provider-sensitive behavior
        async def generate_side_effect(prompt: str, provider: str | None = None):
            return gemini_response if provider == "gemini" else openai_response

        mock_router = MagicMock(spec=AIProviderRouter)
        mock_router.generate = AsyncMock(side_effect=generate_side_effect)
        
        # Test with OpenAI (default)
        agent_openai = TaggingAgent(ai_router=mock_router)
        tags_openai = await agent_openai.suggest_tags("Text")
        assert tags_openai["doc"] == ["doc-tech"]
        
        # Test with Gemini (explicit)
        agent_gemini = TaggingAgent(ai_router=mock_router, ai_provider="gemini")
        tags_gemini = await agent_gemini.suggest_tags("Text")
        assert tags_gemini["doc"] == ["doc-business"]
        
        assert mock_router.generate.await_count == 2


class TestTaggingAgentRouterIntegration:
    """Integration tests with real router behavior"""
    
    @pytest.mark.asyncio
    async def test_agent_with_real_router_mock_providers(self):
        """Test agent with actual router but mocked providers"""
        # Create mock providers
        mock_openai_response = AIResponse(
            text='{"doc": ["doc-tech"], "domain": [], "kb": [], "tool": []}',
            provider="openai",
            model="gpt-4o-mini"
        )
        
        mock_openai = MagicMock()
        mock_openai.name = "openai"
        mock_openai.generate = AsyncMock(return_value=mock_openai_response)
        
        # Create router with mocked providers
        router = AIProviderRouter(
            providers={"openai": mock_openai},
            auto_register=False
        )
        
        # Create agent
        agent = TaggingAgent(ai_router=router)
        
        # Test
        tags = await agent.suggest_tags("Technical content")
        
        assert tags["doc"] == ["doc-tech"]
        mock_openai.generate.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
