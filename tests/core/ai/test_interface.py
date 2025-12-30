"""
Tests for AI Provider Interface and Response Models.

This module tests the base abstractions for multi-AI provider support.
"""

import pytest
from pydantic import ValidationError
from src.core.ai.interface import AIResponse, AIProvider


class TestAIResponse:
    """Tests for AIResponse model"""
    
    def test_create_minimal_response(self):
        """Test creating AIResponse with only required fields"""
        response = AIResponse(
            text="Generated text",
            provider="openai",
            model="gpt-4o-mini"
        )
        
        assert response.text == "Generated text"
        assert response.provider == "openai"
        assert response.model == "gpt-4o-mini"
        assert response.raw is None
        assert response.prompt_tokens is None
        assert response.completion_tokens is None
        assert response.total_tokens is None
    
    def test_create_full_response(self):
        """Test creating AIResponse with all fields"""
        raw_data = {"id": "test-123", "choices": []}
        
        response = AIResponse(
            text="Generated text",
            raw=raw_data,
            provider="openai",
            model="gpt-4o-mini",
            prompt_tokens=50,
            completion_tokens=100,
            total_tokens=150
        )
        
        assert response.text == "Generated text"
        assert response.raw == raw_data
        assert response.provider == "openai"
        assert response.model == "gpt-4o-mini"
        assert response.prompt_tokens == 50
        assert response.completion_tokens == 100
        assert response.total_tokens == 150
    
    def test_optional_fields_can_be_omitted(self):
        """Test that optional fields can be omitted"""
        response = AIResponse(
            text="Test",
            provider="gemini",
            model="gemini-1.5-flash"
        )
        
        # Optional fields should be None
        assert response.raw is None
        assert response.prompt_tokens is None
        assert response.completion_tokens is None
        assert response.total_tokens is None
    
    def test_missing_required_field_raises_error(self):
        """Test that missing required fields raise ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            AIResponse(
                provider="openai",
                model="gpt-4o-mini"
                # Missing 'text' field
            )
        
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("text",)
        assert errors[0]["type"] == "missing"
    
    def test_response_serialization(self):
        """Test that AIResponse can be serialized to dict/JSON"""
        response = AIResponse(
            text="Test response",
            provider="openai",
            model="gpt-4o-mini",
            prompt_tokens=10,
            completion_tokens=20
        )
        
        data = response.model_dump()
        
        assert data["text"] == "Test response"
        assert data["provider"] == "openai"
        assert data["model"] == "gpt-4o-mini"
        assert data["prompt_tokens"] == 10
        assert data["completion_tokens"] == 20
        assert data["raw"] is None
    
    def test_response_with_raw_dict(self):
        """Test AIResponse with raw provider response"""
        raw_response = {
            "id": "chatcmpl-123",
            "object": "chat.completion",
            "created": 1677652288,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "Hello!"
                    }
                }
            ]
        }
        
        response = AIResponse(
            text="Hello!",
            raw=raw_response,
            provider="openai",
            model="gpt-4o-mini"
        )
        
        assert response.raw == raw_response
        assert response.raw["id"] == "chatcmpl-123"
    
    def test_token_counts_validation(self):
        """Test that token counts can be any positive integer"""
        response = AIResponse(
            text="Test",
            provider="gemini",
            model="gemini-1.5-flash",
            prompt_tokens=1000,
            completion_tokens=2000,
            total_tokens=3000
        )
        
        assert response.prompt_tokens == 1000
        assert response.completion_tokens == 2000
        assert response.total_tokens == 3000
    
    def test_provider_names(self):
        """Test different provider names"""
        providers = ["openai", "gemini", "claude", "anthropic", "custom"]
        
        for provider_name in providers:
            response = AIResponse(
                text="Test",
                provider=provider_name,
                model="test-model"
            )
            assert response.provider == provider_name


class TestAIProviderProtocol:
    """Tests for AIProvider protocol"""
    
    def test_protocol_can_be_implemented(self):
        """Test that AIProvider protocol can be implemented by a class"""
        
        class MockProvider:
            name = "mock"
            
            async def generate(self, prompt: str, **kwargs) -> AIResponse:
                return AIResponse(
                    text=f"Mock response to: {prompt}",
                    provider=self.name,
                    model="mock-model-v1"
                )
            
            async def embed(self, text: str, **kwargs) -> list[float]:
                return [0.1, 0.2, 0.3]
            
            async def count_tokens(self, text: str, **kwargs) -> int:
                return len(text.split())
        
        # Verify it implements the protocol
        provider = MockProvider()
        assert hasattr(provider, "name")
        assert hasattr(provider, "generate")
        assert hasattr(provider, "embed")
        assert hasattr(provider, "count_tokens")
    
    @pytest.mark.asyncio
    async def test_mock_provider_generate(self):
        """Test mock provider generate method"""
        
        class MockProvider:
            name = "mock"
            
            async def generate(self, prompt: str, **kwargs) -> AIResponse:
                return AIResponse(
                    text="Generated text",
                    provider=self.name,
                    model="mock-model",
                    prompt_tokens=10,
                    completion_tokens=20,
                    total_tokens=30
                )
            
            async def embed(self, text: str, **kwargs) -> list[float]:
                return []
            
            async def count_tokens(self, text: str, **kwargs) -> int:
                return 0
        
        provider = MockProvider()
        response = await provider.generate("Test prompt")
        
        assert isinstance(response, AIResponse)
        assert response.text == "Generated text"
        assert response.provider == "mock"
        assert response.total_tokens == 30


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
