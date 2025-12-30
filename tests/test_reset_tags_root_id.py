"""
Тести для розширеного функціоналу reset-tags з підтримкою root_id.

Тести перевіряють:
- Базову функціональність з root_id (tree scope)
- Без root_id (space scope)
- Валідацію root_id належності до space_key
- Комбінацію root_id + categories
- Помилки валідації
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.api.routers.bulk_reset_tags import reset_tags_in_space


@pytest.mark.asyncio
async def test_reset_tags_space_scope_without_root_id():
    """
    Тест: reset-tags без root_id → обробляє весь простір (space scope).
    """
    with patch("src.api.routers.bulk_reset_tags.SpaceService") as mock_space_service, \
         patch("src.api.routers.bulk_reset_tags.TagResetService") as mock_reset_service:
        
        # Mock SpaceService
        mock_space_instance = mock_space_service.return_value
        mock_space_instance.get_space_pages = AsyncMock(return_value=[
            {"id": "123", "title": "Page 1"},
            {"id": "456", "title": "Page 2"},
        ])
        
        # Mock TagResetService
        mock_reset_instance = mock_reset_service.return_value
        mock_reset_instance.reset_space_tags = AsyncMock(return_value={
            "total": 2,
            "processed": 2,
            "removed": 0,  # dry_run=True -> removed is always 0
            "to_remove": 2,  # dry_run=True -> shows what would be removed
            "no_tags": 0,
            "errors": 0,
            "dry_run": True,
            "details": []
        })
        
        # Call endpoint
        result = await reset_tags_in_space(
            space_key="TEST",
            categories=None,
            dry_run=True,
            root_id=None
        )
        
        # Assertions
        assert result["scope"] == "space"
        assert result["root_id"] is None
        assert result["total"] == 2
        assert result["processed"] == 2
        assert result["removed"] == 0  # dry_run=True
        assert result["to_remove"] == 2  # dry_run=True
        mock_space_instance.get_space_pages.assert_called_once()
        mock_reset_instance.reset_space_tags.assert_called_once()


@pytest.mark.asyncio
async def test_reset_tags_tree_scope_with_root_id():
    """
    Тест: reset-tags з root_id → обробляє лише дерево (tree scope).
    """
    with patch("src.api.routers.bulk_reset_tags.TagResetService") as mock_reset_service:
        
        # Mock TagResetService
        mock_reset_instance = mock_reset_service.return_value
        mock_reset_instance.confluence = MagicMock()
        mock_reset_instance.confluence.get_page = AsyncMock(return_value={
            "id": "789",
            "title": "Root Page",
            "space": {"key": "TEST"}
        })
        mock_reset_instance.collect_tree_pages = AsyncMock(return_value=[
            "789", "790", "791"
        ])
        mock_reset_instance.reset_tree_tags = AsyncMock(return_value={
            "total": 3,
            "processed": 3,
            "removed": 0,  # dry_run=True
            "to_remove": 2,  # dry_run=True
            "no_tags": 1,
            "errors": 0,
            "dry_run": True,
            "details": []
        })
        
        # Call endpoint
        result = await reset_tags_in_space(
            space_key="TEST",
            categories=None,
            dry_run=True,
            root_id="789"
        )
        
        # Assertions
        assert result["scope"] == "tree"
        assert result["root_id"] == "789"
        assert result["total"] == 3
        assert result["removed"] == 0  # dry_run=True
        assert result["to_remove"] == 2  # dry_run=True
        assert result["processed"] == 3
        mock_reset_instance.confluence.get_page.assert_called_once_with("789", expand="space")
        mock_reset_instance.collect_tree_pages.assert_called_once_with("789")
        mock_reset_instance.reset_tree_tags.assert_called_once()


@pytest.mark.asyncio
async def test_reset_tags_tree_scope_with_categories():
    """
    Тест: root_id + categories → видаляються лише вказані категорії в дереві.
    """
    with patch("src.api.routers.bulk_reset_tags.TagResetService") as mock_reset_service:
        
        # Mock TagResetService
        mock_reset_instance = mock_reset_service.return_value
        mock_reset_instance.confluence = MagicMock()
        mock_reset_instance.confluence.get_page = AsyncMock(return_value={
            "id": "999",
            "space": {"key": "ABC"}
        })
        mock_reset_instance.collect_tree_pages = AsyncMock(return_value=["999", "1000"])
        mock_reset_instance.reset_tree_tags = AsyncMock(return_value={
            "total": 2,  # dry_run=False -> shows actual removed
            "processed": 2,
            "removed": 1,
            "no_tags": 1,
            "errors": 0,
            "dry_run": False,
            "details": []
        })
        
        # Call endpoint
        result = await reset_tags_in_space(
            space_key="ABC",
            categories="doc,kb",
            dry_run=False,
            root_id="999"
        )
        
        # Assertions
        assert result["scope"] == "tree"
        assert result["root_id"] == "999"
        # Verify categories were parsed and passed
        mock_reset_instance.reset_tree_tags.assert_called_once()
        call_args = mock_reset_instance.reset_tree_tags.call_args
        assert call_args[1]["categories"] == ["doc", "kb"]
        assert call_args[1]["dry_run"] is False


@pytest.mark.asyncio
async def test_reset_tags_root_id_wrong_space():
    """
    Тест: root_id належить до іншого space → повертається error.
    """
    with patch("src.api.routers.bulk_reset_tags.TagResetService") as mock_reset_service:
        
        # Mock TagResetService
        mock_reset_instance = mock_reset_service.return_value
        mock_reset_instance.confluence = MagicMock()
        mock_reset_instance.confluence.get_page = AsyncMock(return_value={
            "id": "111",
            "space": {"key": "DIFFERENT"}  # Wrong space
        })
        
        # Call endpoint
        result = await reset_tags_in_space(
            space_key="EXPECTED",
            categories=None,
            dry_run=True,
            root_id="111"
        )
        
        # Assertions
        assert result["errors"] == 1
        assert result["scope"] == "tree"
        assert result["root_id"] == "111"
        assert "does not belong to space" in result["error"]
        assert result["total"] == 0


@pytest.mark.asyncio
async def test_reset_tags_invalid_root_id():
    """
    Тест: невалідний root_id → повертається error.
    """
    with patch("src.api.routers.bulk_reset_tags.TagResetService") as mock_reset_service:
        
        # Mock TagResetService
        mock_reset_instance = mock_reset_service.return_value
        mock_reset_instance.confluence = MagicMock()
        mock_reset_instance.confluence.get_page = AsyncMock(
            side_effect=Exception("Page not found")
        )
        
        # Call endpoint
        result = await reset_tags_in_space(
            space_key="TEST",
            categories=None,
            dry_run=True,
            root_id="invalid_id"
        )
        
        # Assertions
        assert result["errors"] == 1
        assert result["scope"] == "tree"
        assert result["root_id"] == "invalid_id"
        assert "Invalid root_id" in result["error"]


@pytest.mark.asyncio
async def test_reset_tree_tags_service_method():
    """
    Тест: TagResetService.reset_tree_tags правильно обробляє список page_ids.
    """
    from src.services.tag_reset_service import TagResetService
    
    with patch("src.services.tag_reset_service.ConfluenceClient") as mock_client:
        
        # Mock ConfluenceClient
        mock_client_instance = mock_client.return_value
        mock_client_instance.get_page = AsyncMock(side_effect=[
            {"id": "1", "title": "Page 1"},
            {"id": "2", "title": "Page 2"},
            {"id": "3", "title": "Page 3"},
        ])
        mock_client_instance.get_labels = AsyncMock(return_value=[
            "doc-api", "kb-guide", "domain-backend"
        ])
        
        # Create service
        service = TagResetService(confluence_client=mock_client_instance)
        
        # Call reset_tree_tags
        result = await service.reset_tree_tags(
            page_ids=["1", "2", "3"],
            categories=["doc", "kb"],
            dry_run=True
        )
        
        # Assertions
        assert result["total"] == 3
        assert result["processed"] == 3
        assert result["dry_run"] is True
        assert result["removed"] == 0  # dry_run=True
        assert "to_remove" in result  # Should have to_remove field
        assert len(result["details"]) == 3


@pytest.mark.asyncio
async def test_collect_tree_pages_service_method():
    """
    Тест: TagResetService.collect_tree_pages рекурсивно збирає дерево.
    """
    from src.services.tag_reset_service import TagResetService
    
    with patch("src.services.tag_reset_service.ConfluenceClient") as mock_client:
        
        # Mock ConfluenceClient
        mock_client_instance = mock_client.return_value
        mock_client_instance.get_child_pages = AsyncMock(side_effect=[
            ["2", "3"],  # children of 1
            [],          # children of 2
            ["4"],       # children of 3
            []           # children of 4
        ])
        
        # Create service
        service = TagResetService(confluence_client=mock_client_instance)
        
        # Call collect_tree_pages
        result = await service.collect_tree_pages("1")
        
        # Assertions
        assert result == ["1", "2", "3", "4"]
        assert mock_client_instance.get_child_pages.call_count == 4


@pytest.mark.asyncio
async def test_dry_run_response_structure():
    """
    Тест: При dry_run=True респонс має to_remove та to_remove_tags.
    """
    from src.services.tag_reset_service import TagResetService
    
    with patch("src.services.tag_reset_service.ConfluenceClient") as mock_client:
        mock_client_instance = mock_client.return_value
        mock_client_instance.get_labels = AsyncMock(return_value=[
            "doc-api", "kb-guide", "domain-backend"
        ])
        
        service = TagResetService(confluence_client=mock_client_instance)
        
        # Test single page reset with dry_run=True
        result = await service.reset_page_tags(
            page_id="123",
            page_title="Test Page",
            categories=["doc", "kb"],
            dry_run=True
        )
        
        # Assertions for dry_run
        assert result["status"] == "dry_run"
        assert "to_remove_tags" in result
        assert "removed_tags" not in result
        assert "doc-api" in result["to_remove_tags"]
        assert "kb-guide" in result["to_remove_tags"]
        assert "domain-backend" not in result["to_remove_tags"]  # filtered out


@pytest.mark.asyncio
async def test_actual_removal_response_structure():
    """
    Тест: При dry_run=False респонс має removed_tags (не to_remove_tags).
    """
    from src.services.tag_reset_service import TagResetService
    
    with patch("src.services.tag_reset_service.ConfluenceClient") as mock_client:
        mock_client_instance = mock_client.return_value
        mock_client_instance.get_labels = AsyncMock(return_value=[
            "doc-api", "kb-guide"
        ])
        mock_client_instance.remove_labels = AsyncMock(return_value={
            "removed": ["doc-api", "kb-guide"]
        })
        
        service = TagResetService(confluence_client=mock_client_instance)
        
        # Test single page reset with dry_run=False
        result = await service.reset_page_tags(
            page_id="123",
            page_title="Test Page",
            categories=None,
            dry_run=False
        )
        
        # Assertions for actual removal
        assert result["status"] == "removed"
        assert "removed_tags" in result
        assert "to_remove_tags" not in result
        assert result["removed_tags"] == ["doc-api", "kb-guide"]


@pytest.mark.asyncio
async def test_summary_removed_vs_to_remove():
    """
    Тест: Перевірка що summary правильно використовує removed або to_remove.
    """
    from src.services.tag_reset_service import TagResetService
    
    with patch("src.services.tag_reset_service.ConfluenceClient") as mock_client:
        mock_client_instance = mock_client.return_value
        
        # Mock get_page for both dry_run calls
        mock_client_instance.get_page = AsyncMock(side_effect=[
            {"id": "1", "title": "Page 1"},
            {"id": "2", "title": "Page 2"},
            {"id": "1", "title": "Page 1"},  # For second call (dry_run=False)
            {"id": "2", "title": "Page 2"},
        ])
        
        mock_client_instance.get_labels = AsyncMock(return_value=[
            "doc-api", "kb-guide"
        ])
        
        service = TagResetService(confluence_client=mock_client_instance)
        
        # Test with dry_run=True
        result_dry = await service.reset_tree_tags(
            page_ids=["1", "2"],
            categories=None,
            dry_run=True
        )
        
        assert result_dry["removed"] == 0
        assert "to_remove" in result_dry
        assert result_dry["to_remove"] == 2
        assert result_dry["dry_run"] is True
        
        # Test with dry_run=False
        mock_client_instance.remove_labels = AsyncMock(return_value={
            "removed": ["doc-api", "kb-guide"]
        })
        
        result_actual = await service.reset_tree_tags(
            page_ids=["1", "2"],
            categories=None,
            dry_run=False
        )
        
        assert result_actual["removed"] == 2
        assert "to_remove" not in result_actual
        assert result_actual["dry_run"] is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
