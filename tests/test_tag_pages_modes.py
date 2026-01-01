"""
Тести для ендпоінту POST /bulk/tag-pages з whitelist та режимною логікою.

Перевіряє:
- TEST режим: завжди dry_run=True
- SAFE_TEST режим: dry_run керується параметром
- PROD режим: dry_run керується параметром
- Whitelist фільтрацію: тільки дозволені сторінки
- Помилку 403 якщо всі page_ids поза whitelist
"""

import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException
from src.services.bulk_tagging_service import BulkTaggingService


@pytest.fixture
def mock_confluence_client():
    """Mock Confluence client."""
    client = MagicMock()

    async def mock_get_page(page_id):
        return {
            "id": str(page_id),
            "title": f"Test Page {page_id}",
            "body": {"storage": {"value": f"<p>Content for page {page_id}</p>" * 50}},
        }

    client.get_page = AsyncMock(side_effect=mock_get_page)
    client.get_labels = AsyncMock(return_value=["existing-tag"])
    client.update_labels = AsyncMock(return_value={"added": ["new-tag"]})
    
    return client


@pytest.fixture
def mock_whitelist_manager():
    """Mock WhitelistManager."""
    manager = MagicMock()
    
    # Дозволені сторінки: 123, 456, 789
    allowed_ids = {123, 456, 789}
    
    async def mock_get_allowed_ids(space_key, confluence_client):
        return allowed_ids
    
    manager.get_allowed_ids = AsyncMock(side_effect=mock_get_allowed_ids)
    
    return manager


@pytest.fixture
def mock_tagging_agent():
    """Mock TaggingAgent suggest_tags."""
    async def mock_suggest_tags(text):
        return {
            "doc": ["doc-tech"],
            "domain": ["domain-test"],
            "kb": [],
            "tool": []
        }
    
    return mock_suggest_tags


@pytest.mark.asyncio
async def test_tag_pages_test_mode_always_dry_run(
    mock_confluence_client,
    mock_whitelist_manager,
    mock_tagging_agent
):
    """
    TEST режим: завжди dry_run=True, навіть якщо передано dry_run=False.
    """
    with patch.dict(os.environ, {"TAGGING_AGENT_MODE": "TEST"}), \
         patch("src.core.whitelist.whitelist_manager.WhitelistManager", return_value=mock_whitelist_manager), \
         patch("src.agents.tagging_agent.TaggingAgent") as mock_agent_class:
        
        # Налаштування мока агента
        mock_agent_instance = MagicMock()
        mock_agent_instance.suggest_tags = AsyncMock(side_effect=mock_tagging_agent)
        mock_agent_instance.mode = "TEST"
        mock_agent_class.return_value = mock_agent_instance
        
        service = BulkTaggingService(confluence_client=mock_confluence_client)
        
        # Спроба з dry_run=False (має бути проігноровано)
        result = await service.tag_pages(
            page_ids=["123", "456"],
            space_key="TEST",
            dry_run=False
        )
        
        # Перевірки
        assert result["mode"] == "TEST"
        assert result["dry_run"] is True  # Форсовано True у TEST режимі
        assert result["success"] == 2
        assert result["whitelist_enabled"] is True
        
        # Verify no actual writes
        mock_confluence_client.update_labels.assert_not_called()


@pytest.mark.asyncio
async def test_tag_pages_safe_test_mode_respects_dry_run_true(
    mock_confluence_client,
    mock_whitelist_manager,
    mock_tagging_agent
):
    """
    SAFE_TEST режим: dry_run=True → тільки симуляція.
    """
    with patch.dict(os.environ, {"TAGGING_AGENT_MODE": "SAFE_TEST"}), \
         patch("src.core.whitelist.whitelist_manager.WhitelistManager", return_value=mock_whitelist_manager), \
         patch("src.agents.tagging_agent.TaggingAgent") as mock_agent_class:
        
        mock_agent_instance = MagicMock()
        mock_agent_instance.suggest_tags = AsyncMock(side_effect=mock_tagging_agent)
        mock_agent_instance.mode = "SAFE_TEST"
        mock_agent_class.return_value = mock_agent_instance
        
        service = BulkTaggingService(confluence_client=mock_confluence_client)
        
        result = await service.tag_pages(
            page_ids=["123", "456"],
            space_key="TEST",
            dry_run=True
        )
        
        assert result["mode"] == "SAFE_TEST"
        assert result["dry_run"] is True
        assert result["success"] == 2
        
        # No writes
        mock_confluence_client.update_labels.assert_not_called()


@pytest.mark.asyncio
async def test_tag_pages_safe_test_mode_respects_dry_run_false(
    mock_confluence_client,
    mock_whitelist_manager,
    mock_tagging_agent
):
    """
    SAFE_TEST режим: dry_run=False → реальні зміни на whitelist сторінках.
    """
    with patch.dict(os.environ, {"TAGGING_AGENT_MODE": "SAFE_TEST"}), \
         patch("src.core.whitelist.whitelist_manager.WhitelistManager", return_value=mock_whitelist_manager), \
         patch("src.agents.tagging_agent.TaggingAgent") as mock_agent_class:
        
        mock_agent_instance = MagicMock()
        mock_agent_instance.suggest_tags = AsyncMock(side_effect=mock_tagging_agent)
        mock_agent_instance.mode = "SAFE_TEST"
        mock_agent_class.return_value = mock_agent_instance
        
        service = BulkTaggingService(confluence_client=mock_confluence_client)
        
        result = await service.tag_pages(
            page_ids=["123", "456"],
            space_key="TEST",
            dry_run=False
        )
        
        assert result["mode"] == "SAFE_TEST"
        assert result["dry_run"] is False
        assert result["success"] == 2
        
        # Verify writes
        assert mock_confluence_client.update_labels.call_count == 2


@pytest.mark.asyncio
async def test_tag_pages_prod_mode_respects_dry_run_true(
    mock_confluence_client,
    mock_whitelist_manager,
    mock_tagging_agent
):
    """
    PROD режим: dry_run=True → тільки симуляція.
    """
    with patch.dict(os.environ, {"TAGGING_AGENT_MODE": "PROD"}), \
         patch("src.core.whitelist.whitelist_manager.WhitelistManager", return_value=mock_whitelist_manager), \
         patch("src.agents.tagging_agent.TaggingAgent") as mock_agent_class:
        
        mock_agent_instance = MagicMock()
        mock_agent_instance.suggest_tags = AsyncMock(side_effect=mock_tagging_agent)
        mock_agent_instance.mode = "PROD"
        mock_agent_class.return_value = mock_agent_instance
        
        service = BulkTaggingService(confluence_client=mock_confluence_client)
        
        result = await service.tag_pages(
            page_ids=["123", "456"],
            space_key="TEST",
            dry_run=True
        )
        
        assert result["mode"] == "PROD"
        assert result["dry_run"] is True
        assert result["success"] == 2
        
        # No writes
        mock_confluence_client.update_labels.assert_not_called()


@pytest.mark.asyncio
async def test_tag_pages_prod_mode_respects_dry_run_false(
    mock_confluence_client,
    mock_whitelist_manager,
    mock_tagging_agent
):
    """
    PROD режим: dry_run=False → реальні зміни.
    """
    with patch.dict(os.environ, {"TAGGING_AGENT_MODE": "PROD"}), \
         patch("src.core.whitelist.whitelist_manager.WhitelistManager", return_value=mock_whitelist_manager), \
         patch("src.agents.tagging_agent.TaggingAgent") as mock_agent_class:
        
        mock_agent_instance = MagicMock()
        mock_agent_instance.suggest_tags = AsyncMock(side_effect=mock_tagging_agent)
        mock_agent_instance.mode = "PROD"
        mock_agent_class.return_value = mock_agent_instance
        
        service = BulkTaggingService(confluence_client=mock_confluence_client)
        
        result = await service.tag_pages(
            page_ids=["123", "456"],
            space_key="TEST",
            dry_run=False
        )
        
        assert result["mode"] == "PROD"
        assert result["dry_run"] is False
        assert result["success"] == 2
        
        # Verify writes
        assert mock_confluence_client.update_labels.call_count == 2


@pytest.mark.asyncio
async def test_tag_pages_whitelist_filters_pages(
    mock_confluence_client,
    mock_whitelist_manager,
    mock_tagging_agent
):
    """
    Whitelist фільтрація: тільки дозволені сторінки обробляються.
    Дозволені: 123, 456, 789
    Запитані: 123, 999 (999 поза whitelist)
    """
    with patch.dict(os.environ, {"TAGGING_AGENT_MODE": "SAFE_TEST"}), \
         patch("src.core.whitelist.whitelist_manager.WhitelistManager", return_value=mock_whitelist_manager), \
         patch("src.agents.tagging_agent.TaggingAgent") as mock_agent_class:
        
        mock_agent_instance = MagicMock()
        mock_agent_instance.suggest_tags = AsyncMock(side_effect=mock_tagging_agent)
        mock_agent_instance.mode = "SAFE_TEST"
        mock_agent_class.return_value = mock_agent_instance
        
        service = BulkTaggingService(confluence_client=mock_confluence_client)
        
        result = await service.tag_pages(
            page_ids=["123", "999"],  # 999 не в whitelist
            space_key="TEST",
            dry_run=True
        )
        
        # Перевірки
        assert result["total"] == 2  # Загальна кількість запитаних
        assert result["processed"] == 1  # Тільки 123 оброблено
        assert result["success"] == 1
        assert result["skipped_by_whitelist"] == 1  # 999 пропущено
        assert result["whitelist_enabled"] is True


@pytest.mark.asyncio
async def test_tag_pages_all_pages_outside_whitelist_returns_403(
    mock_confluence_client,
    mock_whitelist_manager,
    mock_tagging_agent
):
    """
    Якщо всі page_ids поза whitelist → HTTPException 403.
    """
    with patch.dict(os.environ, {"TAGGING_AGENT_MODE": "SAFE_TEST"}), \
         patch("src.core.whitelist.whitelist_manager.WhitelistManager", return_value=mock_whitelist_manager), \
         patch("src.agents.tagging_agent.TaggingAgent") as mock_agent_class:
        
        mock_agent_instance = MagicMock()
        mock_agent_instance.suggest_tags = AsyncMock(side_effect=mock_tagging_agent)
        mock_agent_instance.mode = "SAFE_TEST"
        mock_agent_class.return_value = mock_agent_instance
        
        service = BulkTaggingService(confluence_client=mock_confluence_client)
        
        # Усі сторінки поза whitelist (whitelist: 123, 456, 789)
        with pytest.raises(HTTPException) as exc_info:
            await service.tag_pages(
                page_ids=["999", "888", "777"],
                space_key="TEST",
                dry_run=True
            )
        
        assert exc_info.value.status_code == 403
        assert "No pages allowed by whitelist" in exc_info.value.detail


@pytest.mark.asyncio
async def test_tag_pages_no_whitelist_entries_returns_403(
    mock_confluence_client,
    mock_tagging_agent
):
    
    empty_whitelist_manager = MagicMock()
    empty_whitelist_manager.get_allowed_ids = AsyncMock(return_value=set())
    
    with patch.dict(os.environ, {"TAGGING_AGENT_MODE": "SAFE_TEST"}), \
         patch("src.core.whitelist.whitelist_manager.WhitelistManager", return_value=empty_whitelist_manager), \
         patch("src.agents.tagging_agent.TaggingAgent") as mock_agent_class:
        
        mock_agent_instance = MagicMock()
        mock_agent_instance.suggest_tags = AsyncMock(side_effect=mock_tagging_agent)
        mock_agent_instance.mode = "SAFE_TEST"
        mock_agent_class.return_value = mock_agent_instance
        
        service = BulkTaggingService(confluence_client=mock_confluence_client)
        
        with pytest.raises(HTTPException) as exc_info:
            await service.tag_pages(
                page_ids=["123", "456"],
                space_key="TEST",
                dry_run=True
            )
        
        assert exc_info.value.status_code == 403
        assert "No whitelist entries" in exc_info.value.detail


@pytest.mark.asyncio
async def test_tag_pages_returns_unified_response_structure(
    mock_confluence_client,
    mock_whitelist_manager,
    mock_tagging_agent
):
    """
    Перевірка структури відповіді.
    """
    with patch.dict(os.environ, {"TAGGING_AGENT_MODE": "TEST"}), \
         patch("src.core.whitelist.whitelist_manager.WhitelistManager", return_value=mock_whitelist_manager), \
         patch("src.agents.tagging_agent.TaggingAgent") as mock_agent_class:
        
        mock_agent_instance = MagicMock()
        mock_agent_instance.suggest_tags = AsyncMock(side_effect=mock_tagging_agent)
        mock_agent_instance.mode = "TEST"
        mock_agent_class.return_value = mock_agent_instance
        
        service = BulkTaggingService(confluence_client=mock_confluence_client)
        
        result = await service.tag_pages(
            page_ids=["123", "456"],
            space_key="TEST",
            dry_run=True
        )
        
        # Структура відповіді
        assert "total" in result
        assert "processed" in result
        assert "success" in result
        assert "errors" in result
        assert "skipped_by_whitelist" in result
        assert "mode" in result
        assert "dry_run" in result
        assert "whitelist_enabled" in result
        assert "details" in result
        
        # Details містять інформацію про кожну сторінку
        assert len(result["details"]) == 2
        for detail in result["details"]:
            assert "page_id" in detail
            assert "status" in detail
            assert "tags" in detail
            assert "dry_run" in detail
