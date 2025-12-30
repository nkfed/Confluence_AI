"""
Тести для TagResetService та ендпоінту POST /bulk/reset-tags/{space_key}.

Перевіряє:
- Скидання тегів на сторінці
- Фільтрацію за категоріями
- Dry-run режим
- Обробку помилок
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from src.services.tag_reset_service import TagResetService


def test_is_ai_tag():
    """Тест визначення AI-тегів."""
    service = TagResetService()
    
    # AI tags
    assert service.is_ai_tag("doc-tech") is True
    assert service.is_ai_tag("domain-helpdesk-site") is True
    assert service.is_ai_tag("kb-overview") is True
    assert service.is_ai_tag("tool-rovo-agent") is True
    
    # Non-AI tags
    assert service.is_ai_tag("custom-tag") is False
    assert service.is_ai_tag("feature") is False


def test_filter_tags_by_categories_all():
    """Тест фільтрації всіх AI-тегів."""
    service = TagResetService()
    
    labels = [
        "doc-tech",
        "domain-helpdesk-site",
        "kb-overview",
        "custom-tag",
        "feature"
    ]
    
    # Filter all AI tags (categories=None)
    result = service.filter_tags_by_categories(labels, categories=None)
    
    assert len(result) == 3
    assert "doc-tech" in result
    assert "domain-helpdesk-site" in result
    assert "kb-overview" in result
    assert "custom-tag" not in result


def test_filter_tags_by_categories_specific():
    """Тест фільтрації за конкретними категоріями."""
    service = TagResetService()
    
    labels = [
        "doc-tech",
        "doc-business",
        "domain-helpdesk-site",
        "kb-overview",
        "tool-rovo-agent"
    ]
    
    # Filter only 'doc' category
    result = service.filter_tags_by_categories(labels, categories=["doc"])
    
    assert len(result) == 2
    assert "doc-tech" in result
    assert "doc-business" in result
    assert "domain-helpdesk-site" not in result


@pytest.mark.asyncio
async def test_reset_page_tags_dry_run():
    """Тест скидання тегів у dry-run режимі."""
    mock_client = MagicMock()
    mock_client.get_labels = AsyncMock(return_value=[
        "doc-tech",
        "domain-helpdesk-site",
        "custom-tag"
    ])
    
    service = TagResetService(confluence_client=mock_client)
    
    result = await service.reset_page_tags(
        page_id="123",
        page_title="Test Page",
        categories=None,
        dry_run=True
    )
    
    # Verify dry-run
    assert result["status"] == "dry_run"
    assert "to_remove_tags" in result  # dry_run uses to_remove_tags
    assert "removed_tags" not in result  # not removed_tags
    assert len(result["to_remove_tags"]) == 2  # Only AI tags
    assert "doc-tech" in result["to_remove_tags"]
    assert "domain-helpdesk-site" in result["to_remove_tags"]
    assert "custom-tag" not in result["to_remove_tags"]
    
    # Verify no actual removal
    mock_client.remove_labels.assert_not_called()


@pytest.mark.asyncio
async def test_reset_page_tags_actual_removal():
    """Тест реального скидання тегів."""
    mock_client = MagicMock()
    mock_client.get_labels = AsyncMock(return_value=[
        "doc-tech",
        "domain-helpdesk-site"
    ])
    mock_client.remove_labels = AsyncMock(return_value={
        "removed": ["doc-tech", "domain-helpdesk-site"],
        "errors": []
    })
    
    service = TagResetService(confluence_client=mock_client)
    
    result = await service.reset_page_tags(
        page_id="123",
        page_title="Test Page",
        categories=None,
        dry_run=False
    )
    
    # Verify actual removal
    assert result["status"] == "removed"
    assert len(result["removed_tags"]) == 2
    mock_client.remove_labels.assert_called_once()


@pytest.mark.asyncio
async def test_reset_page_tags_no_tags():
    """Тест коли немає тегів для видалення."""
    mock_client = MagicMock()
    mock_client.get_labels = AsyncMock(return_value=["custom-tag"])
    
    service = TagResetService(confluence_client=mock_client)
    
    result = await service.reset_page_tags(
        page_id="123",
        page_title="Test Page",
        categories=None,
        dry_run=False
    )
    
    # Verify no removal needed
    assert result["status"] == "no_tags"
    assert "removed_tags" in result  # dry_run=False uses removed_tags
    assert len(result["removed_tags"]) == 0


@pytest.mark.asyncio
async def test_reset_page_tags_category_filter():
    """Тест скидання тегів тільки певної категорії."""
    mock_client = MagicMock()
    mock_client.get_labels = AsyncMock(return_value=[
        "doc-tech",
        "doc-business",
        "domain-helpdesk-site"
    ])
    
    service = TagResetService(confluence_client=mock_client)
    
    result = await service.reset_page_tags(
        page_id="123",
        page_title="Test Page",
        categories=["doc"],  # Only 'doc' category
        dry_run=True
    )
    
    # Verify only doc tags
    assert "to_remove_tags" in result  # dry_run=True
    assert len(result["to_remove_tags"]) == 2
    assert "doc-tech" in result["to_remove_tags"]
    assert "doc-business" in result["to_remove_tags"]
    assert "domain-helpdesk-site" not in result["to_remove_tags"]


@pytest.mark.asyncio
async def test_reset_space_tags():
    """Тест скидання тегів на всіх сторінках простору."""
    pages = [
        {"id": "123", "title": "Page 1"},
        {"id": "456", "title": "Page 2"},
        {"id": "789", "title": "Page 3"}
    ]
    
    mock_client = MagicMock()
    mock_client.get_labels = AsyncMock(side_effect=[
        ["doc-tech", "custom-tag"],  # Page 1
        ["domain-helpdesk-site"],     # Page 2
        ["custom-tag"]                # Page 3 (no AI tags)
    ])
    
    service = TagResetService(confluence_client=mock_client)
    
    result = await service.reset_space_tags(
        pages=pages,
        categories=None,
        dry_run=True
    )
    
    # Verify summary
    assert result["total"] == 3
    assert result["processed"] == 3
    assert result["removed"] == 0  # dry_run=True -> removed is always 0
    assert result["to_remove"] == 2  # Pages 1 and 2 would be processed
    assert result["no_tags"] == 1  # Page 3
    assert result["errors"] == 0
    assert result["dry_run"] is True


@pytest.mark.asyncio
async def test_reset_page_tags_error():
    """Тест обробки помилки при скиданні."""
    mock_client = MagicMock()
    mock_client.get_labels = AsyncMock(side_effect=Exception("API Error"))
    
    service = TagResetService(confluence_client=mock_client)
    
    result = await service.reset_page_tags(
        page_id="123",
        page_title="Test Page",
        categories=None,
        dry_run=False
    )
    
    # Verify error handling
    assert result["status"] == "error"
    assert "API Error" in result["error"]
    assert result["skipped"] is True
