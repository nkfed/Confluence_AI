"""
Tests for OpenAI Provider Implementation.

This module tests the OpenAI client that implements the AIProvider interface.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.core.ai.openai_client import OpenAIClient
from src.core.ai.interface import AIResponse


class TestOpenAIClientInitialization:
    """Tests for OpenAI client initialization"""
    
    def test_init_with_api_key(self):
        """Test initialization with explicit API key"""
        client = OpenAIClient(api_key="test-key-123")
        assert client.name == "openai"
        assert client.api_key == "test-key-123"
        assert client.model_default == "gpt-4o-mini"
    
    def test_init_with_custom_model(self):
        """Test initialization with custom default model"""
        client = OpenAIClient(api_key="test-key", model_default="gpt-4o")
        assert client.model_default == "gpt-4o"
    
    def test_init_without_api_key_raises_error(self):
        """Test that initialization without API key raises ValueError"""
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(ValueError, match="OPENAI_API_KEY is not set"):
                OpenAIClient()
    
    def test_init_with_env_var(self):
        """Test initialization using environment variable"""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'env-key-456'}):
            client = OpenAIClient()
            assert client.api_key == 'env-key-456'


class TestOpenAIClientGenerate:
    """Tests for text generation"""
    
    @pytest.mark.asyncio
    async def test_generate_success(self):
        """Test successful text generation"""
        client = OpenAIClient(api_key="test-key")
        
        # Mock OpenAI response
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="Generated text response"))
        ]
        mock_response.usage = MagicMock(
            prompt_tokens=50,
            completion_tokens=100,
            total_tokens=150
        )
        mock_response.model_dump = MagicMock(return_value={"id": "test-123"})
        
        with patch.object(client.client.chat.completions, 'create', new=AsyncMock(return_value=mock_response)):
            result = await client.generate("Test prompt")
        
        assert isinstance(result, AIResponse)
        assert result.text == "Generated text response"
        assert result.provider == "openai"
        assert result.model == "gpt-4o-mini"
        assert result.prompt_tokens == 50
        assert result.completion_tokens == 100
        assert result.total_tokens == 150
    
    @pytest.mark.asyncio
    async def test_generate_with_custom_model(self):
        """Test generation with custom model"""
        client = OpenAIClient(api_key="test-key")
        
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Response"))]
        mock_response.usage = MagicMock(prompt_tokens=10, completion_tokens=20, total_tokens=30)
        mock_response.model_dump = MagicMock(return_value={})
        
        with patch.object(client.client.chat.completions, 'create', new=AsyncMock(return_value=mock_response)) as mock_create:
            result = await client.generate("Test", model="gpt-4o")
            
            # Verify correct model was used
            mock_create.assert_called_once()
            assert mock_create.call_args[1]['model'] == "gpt-4o"
            assert result.model == "gpt-4o"
    
    @pytest.mark.asyncio
    async def test_generate_with_kwargs(self):
        """Test generation with additional parameters"""
        client = OpenAIClient(api_key="test-key")
        
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Response"))]
        mock_response.usage = None  # Test without usage data
        mock_response.model_dump = MagicMock(return_value={})
        
        with patch.object(client.client.chat.completions, 'create', new=AsyncMock(return_value=mock_response)) as mock_create:
            result = await client.generate(
                "Test",
                temperature=0.8,
                max_tokens=500
            )
            
            # Verify kwargs were passed
            call_kwargs = mock_create.call_args[1]
            assert call_kwargs['temperature'] == 0.8
            assert call_kwargs['max_tokens'] == 500
            
            # Verify None tokens when usage is not provided
            assert result.prompt_tokens is None
            assert result.completion_tokens is None
            assert result.total_tokens is None
    
    @pytest.mark.asyncio
    async def test_generate_rate_limit_retry(self):
        """Test retry logic on rate limit error"""
        client = OpenAIClient(api_key="test-key")
        
        # First call raises rate limit, second succeeds
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Success after retry"))]
        mock_response.usage = MagicMock(prompt_tokens=10, completion_tokens=20, total_tokens=30)
        mock_response.model_dump = MagicMock(return_value={})
        
        mock_create = AsyncMock(
            side_effect=[
                Exception("rate_limit exceeded"),
                mock_response
            ]
        )
        
        with patch.object(client.client.chat.completions, 'create', new=mock_create):
            with patch('asyncio.sleep', new=AsyncMock()):  # Mock sleep to speed up test
                result = await client.generate("Test", max_retries=3)
        
        assert result.text == "Success after retry"
        assert mock_create.call_count == 2
    
    @pytest.mark.asyncio
    async def test_generate_rate_limit_max_retries(self):
        """Test that max retries is respected"""
        client = OpenAIClient(api_key="test-key")
        
        # Always raise rate limit error
        mock_create = AsyncMock(side_effect=Exception("429 rate_limit"))
        
        with patch.object(client.client.chat.completions, 'create', new=mock_create):
            with patch('asyncio.sleep', new=AsyncMock()):
                with pytest.raises(RuntimeError, match="rate limit error after .* attempts"):
                    await client.generate("Test", max_retries=2)
        
        assert mock_create.call_count == 2
    
    @pytest.mark.asyncio
    async def test_generate_other_error_no_retry(self):
        """Test that non-rate-limit errors are not retried"""
        client = OpenAIClient(api_key="test-key")
        
        mock_create = AsyncMock(side_effect=Exception("Authentication error"))
        
        with patch.object(client.client.chat.completions, 'create', new=mock_create):
            with pytest.raises(RuntimeError, match="OpenAI API error"):
                await client.generate("Test")
        
        # Should fail immediately without retries
        assert mock_create.call_count == 1
    
    @pytest.mark.asyncio
    async def test_generate_empty_content(self):
        """Test handling of empty content in response"""
        client = OpenAIClient(api_key="test-key")
        
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content=None))]
        mock_response.usage = None
        mock_response.model_dump = MagicMock(return_value={})
        
        with patch.object(client.client.chat.completions, 'create', new=AsyncMock(return_value=mock_response)):
            result = await client.generate("Test")
        
        assert result.text == ""  # Should handle None gracefully


class TestOpenAIClientEmbed:
    """Tests for embeddings"""
    
    @pytest.mark.asyncio
    async def test_embed_not_implemented(self):
        """Test that embed raises NotImplementedError"""
        client = OpenAIClient(api_key="test-key")
        
        with pytest.raises(NotImplementedError, match="Embeddings not implemented"):
            await client.embed("Test text")


class TestOpenAIClientCountTokens:
    """Tests for token counting"""
    
    @pytest.mark.asyncio
    async def test_count_tokens_not_implemented(self):
        """Test that count_tokens raises NotImplementedError"""
        client = OpenAIClient(api_key="test-key")
        
        with pytest.raises(NotImplementedError, match="Token counting not implemented"):
            await client.count_tokens("Test text")


class TestOpenAIClientProtocolCompliance:
    """Tests for AIProvider protocol compliance"""
    
    def test_has_required_attributes(self):
        """Test that client has all required attributes"""
        client = OpenAIClient(api_key="test-key")
        
        assert hasattr(client, 'name')
        assert hasattr(client, 'generate')
        assert hasattr(client, 'embed')
        assert hasattr(client, 'count_tokens')
    
    def test_name_attribute(self):
        """Test that name attribute is correct"""
        client = OpenAIClient(api_key="test-key")
        assert client.name == "openai"
    
    @pytest.mark.asyncio
    async def test_generate_returns_airesponse(self):
        """Test that generate method returns AIResponse instance"""
        client = OpenAIClient(api_key="test-key")
        
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Test"))]
        mock_response.usage = None
        mock_response.model_dump = MagicMock(return_value={})
        
        with patch.object(client.client.chat.completions, 'create', new=AsyncMock(return_value=mock_response)):
            result = await client.generate("Test")
        
        assert isinstance(result, AIResponse)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
