"""
Integration tests for TaggingAgent with AI Router.

Tests the integration of AI Provider Router with TaggingAgent.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
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
        
        # Mock provider
        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(return_value={"text": "generated text"})
        
        # Mock router
        mock_router = MagicMock(spec=AIProviderRouter)
        mock_router.get = MagicMock(return_value=mock_provider)
        
        # Create agent with router
        agent = TaggingAgent(ai_router=mock_router)
        
        # Suggest tags
        tags = await agent.suggest_tags("This is a technical document about GitHub Copilot")
        
        # Verify router was used
        assert "doc" in tags
        assert "tool" in tags
        mock_router.get.assert_called_once_with(None)  # Default provider
        mock_provider.generate.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_tagging_agent_with_specific_provider(self):
        """Test that TaggingAgent can use specific provider"""
        mock_ai_response = AIResponse(
            text='{"doc": ["doc-business"], "domain": ["domain-ehealth-core"], "kb": [], "tool": []}',
            provider="gemini",
            model="gemini-2.0-flash-exp",
            total_tokens=80
        )
        
        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(return_value=mock_ai_response)
        
        mock_router = MagicMock(spec=AIProviderRouter)
        mock_router.get = MagicMock(return_value=mock_provider)
        
        # Create agent with specific provider
        agent = TaggingAgent(
            ai_router=mock_router,
            ai_provider="gemini"
        )
        
        tags = await agent.suggest_tags("Business document about eHealth")
        
        assert tags["doc"] == ["doc-business"]
        assert tags["domain"] == ["domain-ehealth-core"]
        mock_router.get.assert_called_with("gemini")
    
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
        
        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(return_value=mock_ai_response)
        
        mock_router = MagicMock(spec=AIProviderRouter)
        mock_router.get = MagicMock(return_value=mock_provider)
        
        agent = TaggingAgent(ai_router=mock_router)
        
        tags = await agent.suggest_tags("Some text")
        
        # Should return empty structure when parsing fails
        assert "doc" in tags
        assert "domain" in tags
        assert "kb" in tags
        assert "tool" in tags
    
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
        
        # Mock providers
        mock_openai_provider = MagicMock()
        mock_openai_provider.generate = AsyncMock(return_value=openai_response)
        
        mock_gemini_provider = MagicMock()
        mock_gemini_provider.generate = AsyncMock(return_value=gemini_response)
        
        # Mock router
        def get_provider(name):
            if name == "gemini":
                return mock_gemini_provider
            return mock_openai_provider
        
        mock_router = MagicMock(spec=AIProviderRouter)
        mock_router.get = MagicMock(side_effect=get_provider)
        
        # Test with OpenAI (default)
        agent_openai = TaggingAgent(ai_router=mock_router)
        tags_openai = await agent_openai.suggest_tags("Text")
        assert tags_openai["doc"] == ["doc-tech"]
        
        # Test with Gemini (explicit)
        agent_gemini = TaggingAgent(ai_router=mock_router, ai_provider="gemini")
        tags_gemini = await agent_gemini.suggest_tags("Text")
        assert tags_gemini["doc"] == ["doc-business"]


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
