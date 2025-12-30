"""
Тести для перевірки роботи параметра expand у ConfluenceClient.get_page().

Перевіряє, що метод правильно обробляє різні значення expand:
- За замовчуванням (body.storage,version)
- expand="space"
- expand="" (порожній - без expand)
- expand з кількома значеннями
"""

import pytest
from unittest.mock import patch, MagicMock
from src.clients.confluence_client import ConfluenceClient


@pytest.mark.asyncio
async def test_get_page_default_expand():
    """
    Тест: get_page() без параметра expand використовує за замовчуванням "body.storage,version".
    """
    with patch("src.clients.confluence_client.requests.get") as mock_get:
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "123",
            "title": "Test Page",
            "body": {"storage": {"value": "<p>Content</p>"}}
        }
        mock_get.return_value = mock_response
        
        # Create client and call get_page
        client = ConfluenceClient()
        result = await client.get_page("123")
        
        # Verify the URL contains default expand
        called_url = mock_get.call_args[0][0]
        assert "expand=body.storage,version" in called_url
        assert result["id"] == "123"


@pytest.mark.asyncio
async def test_get_page_with_space_expand():
    """
    Тест: get_page() з expand="space" додає правильний параметр до URL.
    """
    with patch("src.clients.confluence_client.requests.get") as mock_get:
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "456",
            "title": "Test Page",
            "space": {"key": "TEST"}
        }
        mock_get.return_value = mock_response
        
        # Create client and call get_page with expand="space"
        client = ConfluenceClient()
        result = await client.get_page("456", expand="space")
        
        # Verify the URL contains space expand
        called_url = mock_get.call_args[0][0]
        assert "expand=space" in called_url
        assert "body.storage" not in called_url  # Should not have default
        assert result["space"]["key"] == "TEST"


@pytest.mark.asyncio
async def test_get_page_with_empty_expand():
    """
    Тест: get_page() з expand="" не додає параметр expand до URL.
    """
    with patch("src.clients.confluence_client.requests.get") as mock_get:
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "789",
            "title": "Test Page"
        }
        mock_get.return_value = mock_response
        
        # Create client and call get_page with empty expand
        client = ConfluenceClient()
        result = await client.get_page("789", expand="")
        
        # Verify the URL does not contain expand parameter
        called_url = mock_get.call_args[0][0]
        assert "expand" not in called_url
        assert result["id"] == "789"


@pytest.mark.asyncio
async def test_get_page_with_multiple_expand():
    """
    Тест: get_page() з кількома параметрами expand (comma-separated).
    """
    with patch("src.clients.confluence_client.requests.get") as mock_get:
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "999",
            "title": "Test Page",
            "space": {"key": "TEST"},
            "version": {"number": 1}
        }
        mock_get.return_value = mock_response
        
        # Create client and call get_page with multiple expand values
        client = ConfluenceClient()
        result = await client.get_page("999", expand="space,version")
        
        # Verify the URL contains both expand parameters
        called_url = mock_get.call_args[0][0]
        assert "expand=space,version" in called_url
        assert result["space"]["key"] == "TEST"
        assert result["version"]["number"] == 1


@pytest.mark.asyncio
async def test_get_page_backwards_compatibility():
    """
    Тест: старі виклики get_page() без параметра expand працюють як раніше.
    """
    with patch("src.clients.confluence_client.requests.get") as mock_get:
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "111",
            "title": "Old Style Call",
            "body": {"storage": {"value": "<p>Content</p>"}},
            "version": {"number": 1}
        }
        mock_get.return_value = mock_response
        
        # Create client and call get_page without expand (old style)
        client = ConfluenceClient()
        result = await client.get_page("111")
        
        # Should use default expand
        called_url = mock_get.call_args[0][0]
        assert "expand=body.storage,version" in called_url
        assert result["id"] == "111"
        assert "body" in result
        assert "version" in result


@pytest.mark.asyncio
async def test_get_page_error_handling():
    """
    Тест: get_page() правильно обробляє помилки з різними значеннями expand.
    """
    import requests
    
    with patch("src.clients.confluence_client.requests.get") as mock_get:
        # Mock requests.RequestException (which gets converted to RuntimeError)
        mock_get.side_effect = requests.RequestException("Connection error")
        
        # Create client
        client = ConfluenceClient()
        
        # Should raise RuntimeError after retries
        with pytest.raises(RuntimeError, match="Confluence API error"):
            await client.get_page("999", expand="space")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
