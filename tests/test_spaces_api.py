"""
Тести для SpaceService та API ендпоінту GET /spaces.

Перевіряє:
- Отримання списку просторів
- Пагінацію
- Фільтрацію за типами та статусами
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.services.space_service import SpaceService


@pytest.mark.asyncio
async def test_get_spaces_success():
    """Тест успішного отримання списку просторів."""
    # Mock Confluence response
    mock_confluence_data = {
        "results": [
            {
                "id": "1",
                "key": "TEST",
                "name": "Test Space",
                "type": "global",
                "status": "current"
            },
            {
                "id": "2",
                "key": "DOCS",
                "name": "Documentation",
                "type": "global",
                "status": "current"
            }
        ],
        "start": 0,
        "limit": 25,
        "size": 2
    }
    
    # Create mock client
    mock_client = MagicMock()
    mock_client.get_spaces = AsyncMock(return_value=mock_confluence_data)
    
    # Test
    service = SpaceService(confluence_client=mock_client)
    result = await service.get_spaces()
    
    # Verify
    assert result["size"] == 2
    assert result["total"] == 2
    assert len(result["spaces"]) == 2
    assert result["spaces"][0]["key"] == "TEST"
    assert result["spaces"][1]["key"] == "DOCS"


@pytest.mark.asyncio
async def test_get_spaces_with_query():
    """Тест отримання просторів з пошуковим запитом."""
    mock_confluence_data = {
        "results": [
            {
                "id": "1",
                "key": "TEST",
                "name": "Test Space",
                "type": "global",
                "status": "current"
            }
        ],
        "start": 0,
        "limit": 25,
        "size": 1
    }
    
    mock_client = MagicMock()
    mock_client.get_spaces = AsyncMock(return_value=mock_confluence_data)
    
    service = SpaceService(confluence_client=mock_client)
    result = await service.get_spaces(query="TEST")
    
    # Verify query was passed
    mock_client.get_spaces.assert_called_once()
    call_args = mock_client.get_spaces.call_args
    assert call_args[1]["query"] == "TEST"


@pytest.mark.asyncio
async def test_get_spaces_pagination():
    """Тест пагінації."""
    mock_confluence_data = {
        "results": [],
        "start": 25,
        "limit": 25,
        "size": 0
    }
    
    mock_client = MagicMock()
    mock_client.get_spaces = AsyncMock(return_value=mock_confluence_data)
    
    service = SpaceService(confluence_client=mock_client)
    result = await service.get_spaces(start=25, limit=25)
    
    # Verify pagination parameters
    call_args = mock_client.get_spaces.call_args
    assert call_args[1]["start"] == 25
    assert call_args[1]["limit"] == 25


@pytest.mark.asyncio
async def test_get_spaces_with_exclude_types():
    """Тест фільтрації просторів за типами."""
    mock_confluence_data = {
        "results": [
            {"id": "1", "key": "GLOBAL1", "name": "Global 1", "type": "global", "status": "current"},
            {"id": "2", "key": "PERSONAL1", "name": "Personal 1", "type": "personal", "status": "current"},
            {"id": "3", "key": "GLOBAL2", "name": "Global 2", "type": "global", "status": "current"}
        ],
        "start": 0,
        "limit": 25,
        "size": 3
    }
    
    mock_client = MagicMock()
    mock_client.get_spaces = AsyncMock(return_value=mock_confluence_data)
    
    service = SpaceService(confluence_client=mock_client)
    result = await service.get_spaces(exclude_types=["personal"])
    
    # Verify personal excluded
    assert result["size"] == 2
    assert all(s["type"] != "personal" for s in result["spaces"])
    assert result["spaces"][0]["key"] == "GLOBAL1"
    assert result["spaces"][1]["key"] == "GLOBAL2"


@pytest.mark.asyncio
async def test_get_spaces_with_exclude_statuses():
    """Тест фільтрації просторів за статусами."""
    mock_confluence_data = {
        "results": [
            {"id": "1", "key": "CURRENT1", "name": "Current 1", "type": "global", "status": "current"},
            {"id": "2", "key": "ARCHIVED1", "name": "Archived 1", "type": "global", "status": "archived"},
            {"id": "3", "key": "CURRENT2", "name": "Current 2", "type": "global", "status": "current"}
        ],
        "start": 0,
        "limit": 25,
        "size": 3
    }
    
    mock_client = MagicMock()
    mock_client.get_spaces = AsyncMock(return_value=mock_confluence_data)
    
    service = SpaceService(confluence_client=mock_client)
    result = await service.get_spaces(exclude_statuses=["archived"])
    
    # Verify archived excluded
    assert result["size"] == 2
    assert all(s["status"] != "archived" for s in result["spaces"])


@pytest.mark.asyncio
async def test_get_spaces_with_both_filters():
    """Тест фільтрації за типами ТА статусами (OR логіка)."""
    mock_confluence_data = {
        "results": [
            {"id": "1", "key": "GLOBAL_CURRENT", "name": "GC", "type": "global", "status": "current"},
            {"id": "2", "key": "PERSONAL_CURRENT", "name": "PC", "type": "personal", "status": "current"},
            {"id": "3", "key": "GLOBAL_ARCHIVED", "name": "GA", "type": "global", "status": "archived"},
            {"id": "4", "key": "PERSONAL_ARCHIVED", "name": "PA", "type": "personal", "status": "archived"}
        ],
        "start": 0,
        "limit": 25,
        "size": 4
    }
    
    mock_client = MagicMock()
    mock_client.get_spaces = AsyncMock(return_value=mock_confluence_data)
    
    service = SpaceService(confluence_client=mock_client)
    result = await service.get_spaces(
        exclude_types=["personal"],
        exclude_statuses=["archived"]
    )
    
    # OR logic: exclude if type=personal OR status=archived
    # Should keep only: global + current
    assert result["size"] == 1
    assert result["spaces"][0]["key"] == "GLOBAL_CURRENT"


@pytest.mark.asyncio
async def test_get_spaces_with_multiple_exclude_types():
    """Тест виключення декількох типів."""
    mock_confluence_data = {
        "results": [
            {"id": "1", "key": "GLOBAL", "name": "Global", "type": "global", "status": "current"},
            {"id": "2", "key": "PERSONAL", "name": "Personal", "type": "personal", "status": "current"},
            {"id": "3", "key": "TEAM", "name": "Team", "type": "team", "status": "current"}
        ],
        "start": 0,
        "limit": 25,
        "size": 3
    }
    
    mock_client = MagicMock()
    mock_client.get_spaces = AsyncMock(return_value=mock_confluence_data)
    
    service = SpaceService(confluence_client=mock_client)
    result = await service.get_spaces(exclude_types=["personal", "team"])
    
    # Should keep only global
    assert result["size"] == 1
    assert result["spaces"][0]["type"] == "global"


@pytest.mark.asyncio
async def test_get_spaces_no_filters():
    """Тест що без фільтрів всі простори повертаються."""
    mock_confluence_data = {
        "results": [
            {"id": "1", "key": "TEST1", "name": "Test 1", "type": "global", "status": "current"},
            {"id": "2", "key": "TEST2", "name": "Test 2", "type": "personal", "status": "archived"}
        ],
        "start": 0,
        "limit": 25,
        "size": 2
    }
    
    mock_client = MagicMock()
    mock_client.get_spaces = AsyncMock(return_value=mock_confluence_data)
    
    service = SpaceService(confluence_client=mock_client)
    result = await service.get_spaces()
    
    # All spaces returned
    assert result["size"] == 2


@pytest.mark.asyncio
async def test_get_space_pages_success():
    """Тест отримання сторінок простору."""
    mock_pages = [
        {
            "id": "123",
            "title": "Page 1",
            "type": "page",
            "status": "current"
        },
        {
            "id": "456",
            "title": "Page 2",
            "type": "page",
            "status": "current"
        }
    ]
    
    mock_client = MagicMock()
    mock_client.get_pages_in_space = AsyncMock(return_value=mock_pages)
    
    service = SpaceService(confluence_client=mock_client)
    result = await service.get_space_pages("TEST")
    
    # Verify
    assert len(result) == 2
    assert result[0]["id"] == "123"
    assert result[1]["id"] == "456"


@pytest.mark.asyncio
async def test_get_spaces_error_handling():
    """Тест обробки помилок."""
    mock_client = MagicMock()
    mock_client.get_spaces = AsyncMock(side_effect=Exception("API Error"))
    
    service = SpaceService(confluence_client=mock_client)
    
    with pytest.raises(Exception) as exc_info:
        await service.get_spaces()
    
    assert "API Error" in str(exc_info.value)


@pytest.mark.asyncio
async def test_exclude_types_and_statuses_comprehensive():
    """
    Комплексний тест виключення типів та статусів.
    Перевіряє що виключені простори НЕ з'являються у результаті.
    """
    mock_confluence_data = {
        "results": [
            {"id": "1", "key": "GLOBAL_CURRENT", "name": "GC", "type": "global", "status": "current"},
            {"id": "2", "key": "PERSONAL_CURRENT", "name": "PC", "type": "personal", "status": "current"},
            {"id": "3", "key": "TEAM_CURRENT", "name": "TC", "type": "team", "status": "current"},
            {"id": "4", "key": "GLOBAL_ARCHIVED", "name": "GA", "type": "global", "status": "archived"}
        ],
        "start": 0,
        "limit": 25,
        "size": 4
    }
    
    mock_client = MagicMock()
    mock_client.get_spaces = AsyncMock(return_value=mock_confluence_data)
    
    service = SpaceService(confluence_client=mock_client)
    result = await service.get_spaces(
        exclude_types=["personal", "team"],
        exclude_statuses=["archived"]
    )
    
    # Verify only global + current remains
    assert result["size"] == 1
    
    # Verify excluded types not present
    for space in result["spaces"]:
        assert space["type"] not in ["personal", "team"], f"Type {space['type']} should be excluded"
        assert space["status"] not in ["archived"], f"Status {space['status']} should be excluded"
    
    # Verify correct space remains
    assert result["spaces"][0]["key"] == "GLOBAL_CURRENT"
    assert result["spaces"][0]["type"] == "global"
    assert result["spaces"][0]["status"] == "current"


@pytest.mark.asyncio
async def test_exclude_personal_and_archived_spaces():
    """
    Тест що перевіряє реальну фільтрацію через параметри.
    Моделює виклик з Swagger: ?exclude_types=personal&exclude_statuses=archived
    """
    mock_confluence_data = {
        "results": [
            {"id": "1", "key": "GLOBAL_CURRENT", "name": "Global Current", "type": "global", "status": "current"},
            {"id": "2", "key": "PERSONAL_CURRENT", "name": "Personal Current", "type": "personal", "status": "current"},
            {"id": "3", "key": "GLOBAL_ARCHIVED", "name": "Global Archived", "type": "global", "status": "archived"},
            {"id": "4", "key": "PERSONAL_ARCHIVED", "name": "Personal Archived", "type": "personal", "status": "archived"},
            {"id": "5", "key": "COLLABORATION_CURRENT", "name": "Collaboration Current", "type": "collaboration", "status": "current"}
        ],
        "start": 0,
        "limit": 25,
        "size": 5
    }
    
    mock_client = MagicMock()
    mock_client.get_spaces = AsyncMock(return_value=mock_confluence_data)
    
    service = SpaceService(confluence_client=mock_client)
    result = await service.get_spaces(
        exclude_types=["personal"],
        exclude_statuses=["archived"]
    )
    
    # Verify результат
    assert result["size"] == 2, f"Expected 2 spaces, got {result['size']}"
    
    # Verify що personal та archived виключені
    for space in result["spaces"]:
        assert space["type"] != "personal", f"Space {space['key']} has type=personal (should be excluded)"
        assert space["status"] != "archived", f"Space {space['key']} has status=archived (should be excluded)"
    
    # Verify що залишились правильні простори
    result_keys = [s["key"] for s in result["spaces"]]
    assert "GLOBAL_CURRENT" in result_keys
    assert "COLLABORATION_CURRENT" in result_keys
    
    # Verify що виключені НЕ присутні
    assert "PERSONAL_CURRENT" not in result_keys
    assert "GLOBAL_ARCHIVED" not in result_keys
    assert "PERSONAL_ARCHIVED" not in result_keys


@pytest.mark.asyncio
async def test_name_contains_filter():
    """
    Тест фільтрації за підрядком у назві простору.
    """
    mock_confluence_data = {
        "results": [
            {"id": "1", "key": "ESOZ", "name": "ЕСОЗ Медична", "type": "global", "status": "current"},
            {"id": "2", "key": "TEST", "name": "Test Space", "type": "global", "status": "current"},
            {"id": "3", "key": "ESOZ2", "name": "Система ЕСОЗ", "type": "global", "status": "current"},
            {"id": "4", "key": "OTHER", "name": "Other Space", "type": "global", "status": "current"}
        ],
        "start": 0,
        "limit": 25,
        "size": 4
    }
    
    mock_client = MagicMock()
    mock_client.get_spaces = AsyncMock(return_value=mock_confluence_data)
    
    service = SpaceService(confluence_client=mock_client)
    result = await service.get_spaces(name_contains="ЕСОЗ")
    
    # Verify що знайдено 2 простори з ЕСОЗ у назві
    assert result["size"] == 2, f"Expected 2 spaces with ЕСОЗ, got {result['size']}"
    
    # Verify що всі простори містять "есоз" (без урахування регістру)
    for space in result["spaces"]:
        assert "есоз" in space["name"].lower(), f"Space {space['key']} doesn't contain 'есоз' in name"
    
    # Verify що правильні простори залишились
    result_keys = [s["key"] for s in result["spaces"]]
    assert "ESOZ" in result_keys
    assert "ESOZ2" in result_keys
    
    # Verify що інші виключені
    assert "TEST" not in result_keys
    assert "OTHER" not in result_keys


@pytest.mark.asyncio
async def test_name_contains_with_exclude_filters():
    """
    Тест комбінації name_contains з exclude фільтрами.
    """
    mock_confluence_data = {
        "results": [
            {"id": "1", "key": "ESOZ_GLOBAL", "name": "ЕСОЗ Global", "type": "global", "status": "current"},
            {"id": "2", "key": "ESOZ_PERSONAL", "name": "ЕСОЗ Personal", "type": "personal", "status": "current"},
            {"id": "3", "key": "ESOZ_ARCHIVED", "name": "ЕСОЗ Archived", "type": "global", "status": "archived"},
            {"id": "4", "key": "TEST", "name": "Test Space", "type": "global", "status": "current"}
        ],
        "start": 0,
        "limit": 25,
        "size": 4
    }
    
    mock_client = MagicMock()
    mock_client.get_spaces = AsyncMock(return_value=mock_confluence_data)
    
    service = SpaceService(confluence_client=mock_client)
    result = await service.get_spaces(
        name_contains="ЕСОЗ",
        exclude_types=["personal"],
        exclude_statuses=["archived"]
    )
    
    # Verify що залишився тільки ESOZ_GLOBAL
    assert result["size"] == 1, f"Expected 1 space, got {result['size']}"
    assert result["spaces"][0]["key"] == "ESOZ_GLOBAL"
    
    # Verify що в назві є ЕСОЗ
    assert "есоз" in result["spaces"][0]["name"].lower()
    
    # Verify що тип не personal і статус не archived
    assert result["spaces"][0]["type"] != "personal"
    assert result["spaces"][0]["status"] != "archived"



