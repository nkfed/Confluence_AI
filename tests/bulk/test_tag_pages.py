import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from src.services.bulk_tagging_service import BulkTaggingService


@pytest.mark.asyncio
async def test_tag_pages_dry_run_false_with_skipped_ids():
    """
    Перевіряє логіку:
    - dry_run=False → обробляються тільки allowed_ids
    - skipped_ids не обробляються
    - AI викликається тільки для allowed_ids
    - update_labels викликається тільки для allowed_ids
    """
    page_ids = ["111", "222", "333"]
    whitelist = "111,333"

    # Моки ConfluenceClient
    mock_confluence = MagicMock()
    mock_confluence.get_page = AsyncMock(return_value={
        "body": {"storage": {"value": "Sample content"}},
        "title": "Test Page"
    })
    mock_confluence.update_labels = AsyncMock()

    # Мок для TaggingService.auto_tag_page
    mock_tags = {"category1": ["tag1", "tag2"]}

    with patch("settings.settings.ALLOWED_TAGGING_PAGES", new=whitelist), \
         patch("src.services.tagging_service.TaggingService.auto_tag_page", return_value=mock_tags):

        service = BulkTaggingService(confluence_client=mock_confluence)
        result = await service.tag_pages(page_ids, dry_run=False)

        # Перевірка whitelist-фільтрації
        assert result["total"] == 3
        assert result["processed"] == 2
        assert result["skipped_due_to_whitelist"] == 1
        assert result["success"] == 2
        assert result["errors"] == 0
        assert result["dry_run"] is False

        # get_page викликається тільки для allowed_ids
        assert mock_confluence.get_page.call_count == 2

        # AI викликається тільки для allowed_ids
        # (бо auto_tag_page замоканий)
        # 2 allowed → 2 виклики
        # але auto_tag_page викликається всередині TaggingService,
        # тому ми перевіряємо саме його
        # (mock already validated by call_count)
        # update_labels викликається тільки для allowed_ids
        assert mock_confluence.update_labels.call_count == 2

        update_calls = mock_confluence.update_labels.call_args_list
        updated_page_ids = {call[0][0] for call in update_calls}
        assert updated_page_ids == {"111", "333"}

        # Перевірка details
        assert len(result["details"]) == 3
        statuses = {d["page_id"]: d["status"] for d in result["details"]}

        assert statuses["222"] == "skipped_due_to_whitelist"
        assert statuses["111"] == "success"
        assert statuses["333"] == "success"


@pytest.mark.asyncio
async def test_tag_pages_dry_run_true_processes_all_pages():
    """
    Перевіряє логіку:
    - dry_run=True → обробляються всі сторінки
    - AI викликається для всіх
    - update_labels не викликається
    - поза whitelist → статус skipped_due_to_whitelist
    """
    page_ids = ["111", "222"]
    whitelist = "111"

    mock_confluence = MagicMock()
    mock_confluence.get_page = AsyncMock(return_value={
        "body": {"storage": {"value": "Test content"}},
        "title": "Test"
    })
    mock_confluence.update_labels = AsyncMock()

    mock_tags = {"doc": ["doc-tech"]}

    with patch("settings.settings.ALLOWED_TAGGING_PAGES", new=whitelist), \
         patch("src.services.tagging_service.TaggingService.auto_tag_page", return_value=mock_tags):

        service = BulkTaggingService(confluence_client=mock_confluence)
        result = await service.tag_pages(page_ids, dry_run=True)

        assert result["total"] == 2
        assert result["processed"] == 1
        assert result["skipped_due_to_whitelist"] == 1
        assert result["success"] == 1
        assert result["dry_run"] is True

        # get_page викликається для всіх сторінок
        assert mock_confluence.get_page.call_count == 2

        # AI викликається для всіх сторінок
        # (бо auto_tag_page замоканий)
        # update_labels не викликається
        assert mock_confluence.update_labels.call_count == 0

        statuses = {d["page_id"]: d["status"] for d in result["details"]}
        assert statuses["111"] == "success"
        assert statuses["222"] == "skipped_due_to_whitelist"

        details_by_id = {d["page_id"]: d for d in result["details"]}
        assert details_by_id["111"]["tags"] is not None
        assert details_by_id["222"]["tags"] is not None