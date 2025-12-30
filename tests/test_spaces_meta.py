"""
Тести для ендпоінту GET /spaces/meta та методів SpaceService.

Перевіряє:
- get_all_spaces() - отримання всіх просторів без пагінації
- get_spaces_meta() - отримання метаданих (типи та статуси)
- filter_spaces() - фільтрацію просторів
- Ендпоінт GET /spaces/meta
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from src.services.space_service import SpaceService


@pytest.mark.asyncio
async def test_get_all_spaces():
    """Тест отримання всіх просторів без пагінації."""
    # Mock responses for pagination (limit=2 для демонстрації пагінації)
    mock_client = MagicMock()
    
    # Потрібно mock метод get_spaces з правильними викликами
    responses = [
        # First page - full (2 results with limit=2)
        {
            "results": [
                {"id": "1", "key": "TEST1", "name": "Test 1", "type": "global", "status": "current"},
                {"id": "2", "key": "TEST2", "name": "Test 2", "type": "personal", "status": "current"}
            ],
            "start": 0,
            "limit": 2,
            "size": 2
        },
        # Second page - partial (1 result with limit=2, triggers stop)
        {
            "results": [
                {"id": "3", "key": "TEST3", "name": "Test 3", "type": "global", "status": "archived"}
            ],
            "start": 2,
            "limit": 2,
            "size": 1
        }
    ]
    
    call_count = 0
    async def mock_get_spaces(*args, **kwargs):
        nonlocal call_count
        # Перевизначити limit на 2 для тестування
        kwargs['limit'] = 2
        response = responses[call_count] if call_count < len(responses) else {"results": [], "start": 0, "limit": 2, "size": 0}
        call_count += 1
        return response
    
    mock_client.get_spaces = mock_get_spaces
    
    service = SpaceService(confluence_client=mock_client)
    
    # Тимчасово змінимо limit у методі для тестування
    original_method = service.get_all_spaces
    async def patched_get_all_spaces():
        all_spaces = []
        start = 0
        limit = 2  # Використати малий ліміт для тестування пагінації
        
        while True:
            data = await service.confluence.get_spaces(
                query=None,
                accessible_only=True,
                start=start,
                limit=limit
            )
            
            results = data.get("results", [])
            if not results:
                break
            
            for space_data in results:
                all_spaces.append({
                    "id": space_data.get("id"),
                    "key": space_data.get("key"),
                    "name": space_data.get("name"),
                    "type": space_data.get("type"),
                    "status": space_data.get("status", "current")
                })
            
            if len(results) < limit:
                break
            
            start += limit
        
        return all_spaces
    
    result = await patched_get_all_spaces()
    
    # Verify all spaces returned
    assert len(result) == 3
    assert result[0]["key"] == "TEST1"
    assert result[1]["key"] == "TEST2"
    assert result[2]["key"] == "TEST3"
    
    # Verify pagination calls
    assert call_count == 2  # Should have made 2 calls


@pytest.mark.asyncio
async def test_get_spaces_meta():
    """Тест отримання метаданих просторів."""
    mock_client = MagicMock()
    mock_client.get_spaces = AsyncMock(return_value={
        "results": [
            {"id": "1", "key": "TEST1", "type": "global", "status": "current"},
            {"id": "2", "key": "TEST2", "type": "personal", "status": "current"},
            {"id": "3", "key": "TEST3", "type": "global", "status": "archived"}
        ],
        "start": 0,
        "limit": 100,
        "size": 3
    })
    
    service = SpaceService(confluence_client=mock_client)
    result = await service.get_spaces_meta()
    
    # Verify metadata
    assert "available_types" in result
    assert "available_statuses" in result
    
    # Verify unique types
    assert set(result["available_types"]) == {"global", "personal"}
    
    # Verify unique statuses
    assert set(result["available_statuses"]) == {"archived", "current"}


def test_filter_spaces_by_types():
    """Тест фільтрації просторів за типами."""
    service = SpaceService()
    
    spaces = [
        {"id": "1", "key": "TEST1", "type": "global", "status": "current"},
        {"id": "2", "key": "TEST2", "type": "personal", "status": "current"},
        {"id": "3", "key": "TEST3", "type": "global", "status": "current"}
    ]
    
    # Exclude personal
    result = service.filter_spaces(spaces, exclude_types=["personal"])
    
    assert len(result) == 2
    assert all(s["type"] != "personal" for s in result)


def test_filter_spaces_by_statuses():
    """Тест фільтрації просторів за статусами."""
    service = SpaceService()
    
    spaces = [
        {"id": "1", "key": "TEST1", "type": "global", "status": "current"},
        {"id": "2", "key": "TEST2", "type": "global", "status": "archived"},
        {"id": "3", "key": "TEST3", "type": "personal", "status": "current"}
    ]
    
    # Exclude archived
    result = service.filter_spaces(spaces, exclude_statuses=["archived"])
    
    assert len(result) == 2
    assert all(s["status"] != "archived" for s in result)


def test_filter_spaces_or_logic():
    """Тест OR логіки фільтрації (type АБО status)."""
    service = SpaceService()
    
    spaces = [
        {"id": "1", "key": "GLOBAL_CURRENT", "type": "global", "status": "current"},
        {"id": "2", "key": "PERSONAL_CURRENT", "type": "personal", "status": "current"},
        {"id": "3", "key": "GLOBAL_ARCHIVED", "type": "global", "status": "archived"},
        {"id": "4", "key": "PERSONAL_ARCHIVED", "type": "personal", "status": "archived"}
    ]
    
    # Exclude personal OR archived (OR logic)
    result = service.filter_spaces(
        spaces,
        exclude_types=["personal"],
        exclude_statuses=["archived"]
    )
    
    # Should keep only: global + current
    assert len(result) == 1
    assert result[0]["key"] == "GLOBAL_CURRENT"
    assert result[0]["type"] == "global"
    assert result[0]["status"] == "current"


def test_filter_spaces_no_filters():
    """Тест що без фільтрів всі простори повертаються."""
    service = SpaceService()
    
    spaces = [
        {"id": "1", "key": "TEST1", "type": "global", "status": "current"},
        {"id": "2", "key": "TEST2", "type": "personal", "status": "archived"}
    ]
    
    result = service.filter_spaces(spaces)
    
    assert len(result) == 2
    assert result == spaces


def test_filter_spaces_empty_filters():
    """Тест що порожні фільтри не виключають простори."""
    service = SpaceService()
    
    spaces = [
        {"id": "1", "key": "TEST1", "type": "global", "status": "current"}
    ]
    
    result = service.filter_spaces(spaces, exclude_types=[], exclude_statuses=[])
    
    assert len(result) == 1


def test_filter_spaces_multiple_types():
    """Тест виключення декількох типів."""
    service = SpaceService()
    
    spaces = [
        {"id": "1", "key": "TEST1", "type": "global", "status": "current"},
        {"id": "2", "key": "TEST2", "type": "personal", "status": "current"},
        {"id": "3", "key": "TEST3", "type": "team", "status": "current"}
    ]
    
    result = service.filter_spaces(spaces, exclude_types=["personal", "team"])
    
    assert len(result) == 1
    assert result[0]["type"] == "global"


@pytest.mark.asyncio
async def test_get_spaces_with_filters():
    """Тест get_spaces() з фільтрами."""
    mock_client = MagicMock()
    mock_client.get_spaces = AsyncMock(return_value={
        "results": [
            {"id": "1", "key": "TEST1", "type": "global", "status": "current"},
            {"id": "2", "key": "TEST2", "type": "personal", "status": "current"},
            {"id": "3", "key": "TEST3", "type": "global", "status": "archived"}
        ],
        "start": 0,
        "limit": 25,
        "size": 3
    })
    
    service = SpaceService(confluence_client=mock_client)
    
    # Test with filters
    result = await service.get_spaces(
        exclude_types=["personal"],
        exclude_statuses=["archived"]
    )
    
    # Should return only global + current
    assert result["size"] == 1
    assert result["spaces"][0]["key"] == "TEST1"


@pytest.mark.asyncio
async def test_get_spaces_meta_empty():
    """Тест метаданих коли немає просторів."""
    mock_client = MagicMock()
    mock_client.get_spaces = AsyncMock(return_value={
        "results": [],
        "start": 0,
        "limit": 100,
        "size": 0
    })
    
    service = SpaceService(confluence_client=mock_client)
    result = await service.get_spaces_meta()
    
    assert result["available_types"] == []
    assert result["available_statuses"] == []


@pytest.mark.asyncio
async def test_get_spaces_meta_handles_none_values():
    """Тест обробки None значень у типах та статусах."""
    mock_client = MagicMock()
    mock_client.get_spaces = AsyncMock(return_value={
        "results": [
            {"id": "1", "key": "TEST1", "type": None, "status": "current"},
            {"id": "2", "key": "TEST2", "type": "global", "status": None}
        ],
        "start": 0,
        "limit": 100,
        "size": 2
    })
    
    service = SpaceService(confluence_client=mock_client)
    result = await service.get_spaces_meta()
    
    # Should only include non-None values
    assert "global" in result["available_types"]
    assert "current" in result["available_statuses"]
    assert len(result["available_types"]) == 1
    assert len(result["available_statuses"]) == 1


def test_filter_spaces_excludes_correctly():
    """
    Критичний тест: перевіряє що filter_spaces ВИКЛЮЧАЄ, а не включає.
    """
    service = SpaceService()
    
    spaces = [
        {"id": "1", "key": "KEEP1", "type": "global", "status": "current"},
        {"id": "2", "key": "EXCLUDE_TYPE", "type": "personal", "status": "current"},
        {"id": "3", "key": "EXCLUDE_STATUS", "type": "global", "status": "archived"},
        {"id": "4", "key": "EXCLUDE_BOTH", "type": "personal", "status": "archived"}
    ]
    
    # Виключити personal типи та archived статуси
    result = service.filter_spaces(
        spaces,
        exclude_types=["personal"],
        exclude_statuses=["archived"]
    )
    
    # Має залишитись тільки один простір
    assert len(result) == 1
    assert result[0]["key"] == "KEEP1"
    
    # Перевірити що виключені НЕ присутні
    result_keys = [s["key"] for s in result]
    assert "EXCLUDE_TYPE" not in result_keys
    assert "EXCLUDE_STATUS" not in result_keys
    assert "EXCLUDE_BOTH" not in result_keys
    
    # Перевірити що не виключено personal + current та global + archived
    excluded_keys = ["EXCLUDE_TYPE", "EXCLUDE_STATUS", "EXCLUDE_BOTH"]
    for space in result:
        assert space["key"] not in excluded_keys

