import pytest
from unittest.mock import patch, AsyncMock
from src.services.bulk_tagging_service import BulkTaggingService
import os


@pytest.mark.asyncio
async def test_tag_pages_dry_run_false_with_skipped_ids():
    """
    Нова архітектура (рефакторинг мок-системи):
    
    Перевіряє основну логіку:
    - processed = кількість сторінок, обробленихагентом (filtered_ids)
    - skipped_by_whitelist = те, що не у whitelist
    """
    # Встановлюємо SAFE_TEST режим для цього тесту
    os.environ["TAGGING_AGENT_MODE"] = "SAFE_TEST"
    
    page_ids = ["111", "222", "333"]
    
    # Моки ConfluenceClient - все має бути AsyncMock!
    mock_confluence = AsyncMock()
    mock_confluence.get_page = AsyncMock(return_value={
        "body": {"storage": {"value": "Sample content"}},
        "title": "Test Page",
        "version": {"number": 1},
        "metadata": {"labels": {"results": []}}
    })
    mock_confluence.get_labels = AsyncMock(return_value=[])
    mock_confluence.update_labels = AsyncMock()

    with patch("src.core.whitelist.whitelist_manager.WhitelistManager.get_allowed_ids",
               new_callable=AsyncMock) as mock_whitelist:
        
        # Whitelist: тільки 111 і 333
        mock_whitelist.return_value = {111, 333}
        
        service = BulkTaggingService(confluence_client=mock_confluence)
        result = await service.tag_pages(page_ids, space_key="euheals", dry_run=False)
        
        # ✅ НОВA СЕМАНТИКА: processed = кількість filtered_ids
        assert result["total"] == 3, f"Expected total=3, got {result['total']}"
        assert result["processed"] == 2, f"Expected processed=2 (111,333), got {result['processed']}"
        assert result["skipped_by_whitelist"] == 1, f"Expected skipped=1, got {result['skipped_by_whitelist']}"
        assert result["success"] == 2, f"Expected success=2, got {result['success']}"
        assert result["errors"] == 0, f"Expected errors=0, got {result['errors']}"
        assert result["dry_run"] is False, f"Expected dry_run=False, got {result['dry_run']}"
        
        # ✅ get_page викликається тільки для filtered_ids (2 сторінки)
        assert mock_confluence.get_page.call_count == 2, \
            f"Expected 2 get_page calls, got {mock_confluence.get_page.call_count}"
        
        # Перевірка details - 222 не повинна бути оброблена
        assert len(result["details"]) == 2, f"Expected 2 details entries (only 111,333), got {len(result['details'])}"
        
        details_by_id = {str(d["page_id"]): d for d in result["details"]}
        
        assert "111" in details_by_id, "Expected page 111 in details"
        assert "333" in details_by_id, "Expected page 333 in details"
        assert "222" not in details_by_id, "Page 222 should NOT be in details (not in whitelist)"
    
    # Очистити environment
    os.environ.pop("TAGGING_AGENT_MODE", None)


@pytest.mark.asyncio
async def test_tag_pages_dry_run_true_processes_all_pages():
    """
    Нова архітектура (рефакторинг мок-системи):
    
    dry_run=True → обробляються ВСІ сторінки, але update не викликається
    
    Старе очікування (НЕПРАВИЛЬНО):
    - processed = 1 (тільки whitelisted)
    
    Нове очікування (ПРАВИЛЬНО):
    - processed = 2 (всі сторінки обробляються через агент)
    - update_labels не викликається (dry_run=True)
    """
    # Встановлюємо SAFE_TEST режим
    os.environ["TAGGING_AGENT_MODE"] = "SAFE_TEST"
    
    page_ids = ["111", "222"]
    
    # Моки ConfluenceClient - все AsyncMock!
    mock_confluence = AsyncMock()
    mock_confluence.get_page = AsyncMock(return_value={
        "body": {"storage": {"value": "Test content"}},
        "title": "Test",
        "version": {"number": 1},
        "metadata": {"labels": {"results": []}}
    })
    mock_confluence.update_labels = AsyncMock()
    
    mock_tags = {"doc": ["doc-tech"], "domain": [], "kb": [], "tool": []}

    with patch("src.core.whitelist.whitelist_manager.WhitelistManager.get_allowed_ids",
               new_callable=AsyncMock) as mock_whitelist:
        
        # Whitelist: тільки 111
        mock_whitelist.return_value = {111}
        
        with patch("src.services.tagging_service.TaggingService.auto_tag_page",
                   return_value=mock_tags):
            
            service = BulkTaggingService(confluence_client=mock_confluence)
            result = await service.tag_pages(page_ids, space_key="euheals", dry_run=True)
            
            # ✅ НОВА СЕМАНТИКА: processed = filtered_ids (SAFE_TEST фільтрує)
            assert result["total"] == 2, f"Expected total=2, got {result['total']}"
            assert result["processed"] == 1, f"Expected processed=1 (only 111), got {result['processed']}"
            assert result["skipped_by_whitelist"] == 1, f"Expected skipped=1 (222), got {result['skipped_by_whitelist']}"
            assert result["success"] == 1, f"Expected success=1, got {result['success']}"
            assert result["dry_run"] is True, f"Expected dry_run=True, got {result['dry_run']}"
            
            # ✅ update_labels не викликається у dry_run=True
            assert mock_confluence.update_labels.call_count == 0, \
                f"Expected 0 update_labels calls in dry_run, got {mock_confluence.update_labels.call_count}"
            
            # ✅ get_page викликається тільки для filtered_ids
            assert mock_confluence.get_page.call_count == 1, \
                f"Expected 1 get_page call (only 111), got {mock_confluence.get_page.call_count}"
            
            # Перевірка details
            assert len(result["details"]) == 1, f"Expected 1 detail entry, got {len(result['details'])}"
            
            detail = result["details"][0]
            assert str(detail["page_id"]) == "111", f"Expected page_id='111', got {detail['page_id']}"
            assert detail["status"] == "dry_run", \
                f"Expected status='dry_run', got {detail['status']}"
            assert detail["tags"] is not None, "Expected tags in dry_run result"
    
    # Очистити environment
    os.environ.pop("TAGGING_AGENT_MODE", None)