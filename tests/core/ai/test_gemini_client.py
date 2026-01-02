"""
Tests for Google Gemini Provider Implementation.

This module tests the Gemini client that implements the AIProvider interface.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx
from src.core.ai.gemini_client import GeminiClient
from src.core.ai.interface import AIResponse


class TestGeminiClientInitialization:
    """Tests for Gemini client initialization"""
    
    def test_init_with_api_key(self):
        """Test initialization with explicit API key"""
        client = GeminiClient(api_key="test-key-123")
        assert client.name == "gemini"
        assert client.api_key == "test-key-123"
        assert client.model_default == "gemini-2.0-flash-exp"
    
    def test_init_with_custom_model(self):
        """Test initialization with custom default model"""
        client = GeminiClient(api_key="test-key", model_default="gemini-1.5-pro")
        assert client.model_default == "gemini-1.5-pro"
    
    def test_init_without_api_key_raises_error(self):
        """Test that initialization without API key raises ValueError"""
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(ValueError, match="Gemini API key is not set"):
                GeminiClient()
    
    def test_init_with_gemini_api_key_env(self):
        """Test initialization using GEMINI_API_KEY environment variable"""
        with patch.dict('os.environ', {'GEMINI_API_KEY': 'env-key-456'}):
            client = GeminiClient()
            assert client.api_key == 'env-key-456'
    
    def test_init_with_google_api_key_env(self):
        """Test initialization using GOOGLE_API_KEY environment variable"""
        with patch.dict('os.environ', {'GOOGLE_API_KEY': 'google-key-789'}, clear=True):
            client = GeminiClient()
            assert client.api_key == 'google-key-789'
    
    def test_init_with_custom_timeout(self):
        """Test initialization with custom timeout"""
        client = GeminiClient(api_key="test-key", timeout=60.0)
        assert client._client.timeout.connect == 60.0


class TestGeminiClientGenerate:
    """Tests for text generation"""
    
    @pytest.mark.asyncio
    async def test_generate_success(self):
        """Test successful text generation"""
        client = GeminiClient(api_key="test-key")
        
        # Mock Gemini response
        mock_response_data = {
            "candidates": [
                {
                    "content": {
                        "parts": [{"text": "Generated text response from Gemini"}]
                    }
                }
            ],
            "usageMetadata": {
                "promptTokenCount": 10,
                "candidatesTokenCount": 20,
                "totalTokenCount": 30
            }
        }
        
        mock_response = MagicMock()
        mock_response.json.return_value = mock_response_data
        mock_response.status_code = 200
        
        with patch.object(client._client, 'post', new=AsyncMock(return_value=mock_response)):
            result = await client.generate("Test prompt")
        
        assert isinstance(result, AIResponse)
        assert result.text == "Generated text response from Gemini"
        assert result.provider == "gemini"
        assert result.model == "models/gemini-2.0-flash-exp"
        assert result.prompt_tokens == 10
        assert result.completion_tokens == 20
        assert result.total_tokens == 30
    
    @pytest.mark.asyncio
    async def test_generate_with_custom_model(self):
        """Test generation with custom model"""
        client = GeminiClient(api_key="test-key")
        
        mock_response_data = {
            "candidates": [{"content": {"parts": [{"text": "Response"}]}}],
            "usageMetadata": {"totalTokenCount": 15}
        }
        
        mock_response = MagicMock()
        mock_response.json.return_value = mock_response_data
        mock_response.status_code = 200
        
        with patch.object(client._client, 'post', new=AsyncMock(return_value=mock_response)) as mock_post:
            result = await client.generate("Test", model="gemini-1.5-pro")
            
            # Verify correct model was used in URL
            call_args = mock_post.call_args
            assert "models/gemini-1.5-pro:generateContent" in call_args[0][0]
            assert result.model == "models/gemini-1.5-pro"
    
    @pytest.mark.asyncio
    async def test_generate_with_kwargs(self):
        """Test generation with additional parameters"""
        client = GeminiClient(api_key="test-key")
        
        mock_response_data = {
            "candidates": [{"content": {"parts": [{"text": "Response"}]}}],
            "usageMetadata": {}
        }
        
        mock_response = MagicMock()
        mock_response.json.return_value = mock_response_data
        mock_response.status_code = 200
        
        with patch.object(client._client, 'post', new=AsyncMock(return_value=mock_response)) as mock_post:
            result = await client.generate(
                "Test",
                temperature=0.8,
                max_tokens=500,
                top_p=0.95,
                top_k=40
            )
            
            # Verify generation config was included
            call_kwargs = mock_post.call_args[1]
            payload = call_kwargs['json']
            assert 'generationConfig' in payload
            assert payload['generationConfig']['temperature'] == 0.8
            assert payload['generationConfig']['maxOutputTokens'] == 500
            assert payload['generationConfig']['topP'] == 0.95
            assert payload['generationConfig']['topK'] == 40
    
    @pytest.mark.asyncio
    async def test_generate_multiple_text_parts(self):
        """Test handling response with multiple text parts"""
        client = GeminiClient(api_key="test-key")
        
        mock_response_data = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {"text": "Part 1"},
                            {"text": "Part 2"},
                            {"text": "Part 3"}
                        ]
                    }
                }
            ],
            "usageMetadata": {"totalTokenCount": 10}
        }
        
        mock_response = MagicMock()
        mock_response.json.return_value = mock_response_data
        mock_response.status_code = 200
        
        with patch.object(client._client, 'post', new=AsyncMock(return_value=mock_response)):
            result = await client.generate("Test")
        
        assert result.text == "Part 1\nPart 2\nPart 3"
    
    @pytest.mark.asyncio
    async def test_generate_empty_response(self):
        """Test handling of empty response"""
        client = GeminiClient(api_key="test-key")
        
        mock_response_data = {
            "candidates": [],
            "usageMetadata": {}
        }
        
        mock_response = MagicMock()
        mock_response.json.return_value = mock_response_data
        mock_response.status_code = 200
        
        with patch.object(client._client, 'post', new=AsyncMock(return_value=mock_response)):
            result = await client.generate("Test")
        
        assert result.text == ""
        assert result.prompt_tokens is None
    
    @pytest.mark.asyncio
    async def test_generate_rate_limit_retry(self):
        """Test retry logic on rate limit error"""
        client = GeminiClient(api_key="test-key")
        
        # First call raises 429, second succeeds
        error_response = MagicMock()
        error_response.status_code = 429
        error_response.json.return_value = {"error": "rate limit"}
        
        success_response = MagicMock()
        success_response.json.return_value = {
            "candidates": [{"content": {"parts": [{"text": "Success after retry"}]}}],
            "usageMetadata": {"totalTokenCount": 10}
        }
        success_response.status_code = 200
        
        mock_post = AsyncMock(
            side_effect=[
                httpx.HTTPStatusError("429", request=MagicMock(), response=error_response),
                success_response
            ]
        )
        
        with patch.object(client._client, 'post', new=mock_post):
            with patch('asyncio.sleep', new=AsyncMock()):
                result = await client.generate("Test", max_retries=3)
        
        assert result.text == "Success after retry"
        assert mock_post.call_count == 2
    
    @pytest.mark.asyncio
    async def test_generate_rate_limit_max_retries(self):
        """Test that max retries is respected"""
        client = GeminiClient(api_key="test-key")
        
        error_response = MagicMock()
        error_response.status_code = 429
        
        mock_post = AsyncMock(
            side_effect=httpx.HTTPStatusError("429", request=MagicMock(), response=error_response)
        )
        
        with patch.object(client._client, 'post', new=mock_post):
            with patch('asyncio.sleep', new=AsyncMock()):
                with pytest.raises(RuntimeError, match="rate limit error after .* attempts"):
                    await client.generate("Test", max_retries=2)
        
        assert mock_post.call_count == 2
    
    @pytest.mark.asyncio
    async def test_generate_http_error_no_retry(self):
        """Test that non-rate-limit HTTP errors are not retried"""
        client = GeminiClient(api_key="test-key")
        
        error_response = MagicMock()
        error_response.status_code = 400
        error_response.json.return_value = {"error": "Bad request"}
        
        mock_post = AsyncMock(
            side_effect=httpx.HTTPStatusError("400", request=MagicMock(), response=error_response)
        )
        
        with patch.object(client._client, 'post', new=mock_post):
            with pytest.raises(RuntimeError, match="Gemini API HTTP error"):
                await client.generate("Test")
        
        # Should fail immediately without retries
        assert mock_post.call_count == 1
    
    @pytest.mark.asyncio
    async def test_generate_model_prefix_handling(self):
        """Test that model name prefix is handled correctly"""
        client = GeminiClient(api_key="test-key")
        
        mock_response_data = {
            "candidates": [{"content": {"parts": [{"text": "Response"}]}}],
            "usageMetadata": {}
        }
        
        mock_response = MagicMock()
        mock_response.json.return_value = mock_response_data
        mock_response.status_code = 200
        
        with patch.object(client._client, 'post', new=AsyncMock(return_value=mock_response)) as mock_post:
            # Test with model name without prefix
            await client.generate("Test", model="gemini-1.5-flash")
            
            call_args = mock_post.call_args
            assert "models/gemini-1.5-flash:generateContent" in call_args[0][0]


class TestGeminiClientCountTokens:
    """Tests for token counting"""
    
    @pytest.mark.asyncio
    async def test_count_tokens_success(self):
        """Test successful token counting"""
        client = GeminiClient(api_key="test-key")
        
        mock_response_data = {"totalTokens": 42}
        
        mock_response = MagicMock()
        mock_response.json.return_value = mock_response_data
        mock_response.status_code = 200
        
        with patch.object(client._client, 'post', new=AsyncMock(return_value=mock_response)):
            result = await client.count_tokens("Test text for counting tokens")
        
        assert result == 42
    
    @pytest.mark.asyncio
    async def test_count_tokens_with_custom_model(self):
        """Test token counting with custom model"""
        client = GeminiClient(api_key="test-key")
        
        mock_response_data = {"totalTokens": 15}
        
        mock_response = MagicMock()
        mock_response.json.return_value = mock_response_data
        mock_response.status_code = 200
        
        with patch.object(client._client, 'post', new=AsyncMock(return_value=mock_response)) as mock_post:
            result = await client.count_tokens("Test", model="gemini-1.5-pro")
            
            # Verify correct model was used
            call_args = mock_post.call_args
            assert "models/gemini-1.5-pro:countTokens" in call_args[0][0]
            assert result == 15
    
    @pytest.mark.asyncio
    async def test_count_tokens_error(self):
        """Test token counting error handling"""
        client = GeminiClient(api_key="test-key")
        
        error_response = MagicMock()
        error_response.status_code = 400
        
        mock_post = AsyncMock(
            side_effect=httpx.HTTPStatusError("400", request=MagicMock(), response=error_response)
        )
        
        with patch.object(client._client, 'post', new=mock_post):
            with pytest.raises(RuntimeError, match="Gemini token counting error"):
                await client.count_tokens("Test")
    
    @pytest.mark.asyncio
    async def test_count_tokens_zero(self):
        """Test token counting with zero tokens"""
        client = GeminiClient(api_key="test-key")
        
        mock_response_data = {"totalTokens": 0}
        
        mock_response = MagicMock()
        mock_response.json.return_value = mock_response_data
        mock_response.status_code = 200
        
        with patch.object(client._client, 'post', new=AsyncMock(return_value=mock_response)):
            result = await client.count_tokens("")
        
        assert result == 0


class TestGeminiClientEmbed:
    """Tests for embeddings"""
    
    @pytest.mark.asyncio
    async def test_embed_not_implemented(self):
        """Test that embed raises NotImplementedError"""
        client = GeminiClient(api_key="test-key")
        
        with pytest.raises(NotImplementedError, match="Embeddings not implemented"):
            await client.embed("Test text")


class TestGeminiClientProtocolCompliance:
    """Tests for AIProvider protocol compliance"""
    
    def test_has_required_attributes(self):
        """Test that client has all required attributes"""
        client = GeminiClient(api_key="test-key")
        
        assert hasattr(client, 'name')
        assert hasattr(client, 'generate')
        assert hasattr(client, 'embed')
        assert hasattr(client, 'count_tokens')
    
    def test_name_attribute(self):
        """Test that name attribute is correct"""
        client = GeminiClient(api_key="test-key")
        assert client.name == "gemini"
    
    @pytest.mark.asyncio
    async def test_generate_returns_airesponse(self):
        """Test that generate method returns AIResponse instance"""
        client = GeminiClient(api_key="test-key")
        
        mock_response_data = {
            "candidates": [{"content": {"parts": [{"text": "Test"}]}}],
            "usageMetadata": {}
        }
        
        mock_response = MagicMock()
        mock_response.json.return_value = mock_response_data
        mock_response.status_code = 200
        
        with patch.object(client._client, 'post', new=AsyncMock(return_value=mock_response)):
            result = await client.generate("Test")
        
        assert isinstance(result, AIResponse)
    
    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test async context manager support"""
        async with GeminiClient(api_key="test-key") as client:
            assert client.name == "gemini"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
