import pytest
from unittest.mock import AsyncMock, patch
from src.services.bulk_tagging_service import BulkTaggingService


@pytest.mark.asyncio
async def test_context_limiting_applies_to_tag_tree():
    confluence = AsyncMock()
    confluence.get_child_pages = AsyncMock(return_value=[])
    confluence.get_page = AsyncMock(return_value={"body": {"storage": {"value": "<p>Tree</p>"}}})
    confluence.get_labels = AsyncMock(return_value=[])

    service = BulkTaggingService(confluence_client=confluence)

    with patch("src.core.whitelist.whitelist_manager.WhitelistManager.get_allowed_ids", AsyncMock(return_value={1})), \
         patch("src.services.bulk_tagging_service.BulkTaggingService._collect_all_children", AsyncMock(return_value=["1"])), \
         patch("src.services.bulk_tagging_service.prepare_ai_context") as mock_ctx:
        mock_ctx.return_value = "ctx"

        await service.tag_tree(root_page_id="1", space_key="euheals", dry_run=True)

        assert mock_ctx.call_count == 1


@pytest.mark.asyncio
@pytest.mark.skip(reason="Requires whitelist refactoring for space filtering")
async def test_context_limiting_applies_to_tag_space():
    """
    TODO: This test requires proper mocking of whitelist manager
    for space-level filtering. Current implementation uses entry_points
    which filters at tag_pages level, not tag_space level.
    """
    confluence = AsyncMock()
    confluence.get_all_pages_in_space = AsyncMock(return_value=["111", "222"])
    confluence.get_page = AsyncMock(return_value={"body": {"storage": {"value": "<p>Space</p>"}}})
    confluence.get_labels = AsyncMock(return_value=[])

    service = BulkTaggingService(confluence_client=confluence)

    # Mock both entry points and is_page_allowed to allow our test pages
    with patch("src.core.whitelist.whitelist_manager.WhitelistManager.get_entry_points", return_value=[111, 222]), \
         patch("src.services.bulk_tagging_service.prepare_ai_context") as mock_ctx:
        mock_ctx.return_value = "ctx"

        await service.tag_space(space_key="euheals", dry_run=True)

        assert mock_ctx.call_count == 2
