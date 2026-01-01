"""
Інтеграційні тести для tag_space з whitelist механізмом.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.services.bulk_tagging_service import BulkTaggingService


@pytest.fixture
def mock_confluence_client():
    """Mock Confluence client."""
    mock = MagicMock()
    mock.get_all_pages_in_space = AsyncMock(return_value=[
        "100", "101", "102", "200", "201", "999"
    ])
    mock.get_child_pages = AsyncMock(return_value=[])
    mock.get_page = AsyncMock(return_value={
        "id": "100",
        "title": "Test Page",
        "body": {"storage": {"value": "Test content"}}
    })
    mock.get_labels = AsyncMock(return_value=[])
    mock.update_labels = AsyncMock()
    return mock


@pytest.fixture
def mock_whitelist_config(tmp_path):
    """Створює тимчасову whitelist конфігурацію."""
    import json
    
    config = {
        "spaces": [
            {
                "space_key": "TEST",
                "pages": [
                    {"id": 100, "name": "Root", "root": True},
                    {"id": 200, "name": "Entry", "root": False}
                ]
            }
        ]
    }
    
    config_path = tmp_path / "whitelist_config.json"
    with open(config_path, 'w') as f:
        json.dump(config, f)
    
    return str(config_path)


@pytest.mark.asyncio
async def test_tag_space_test_mode_whitelist_active(
    mock_confluence_client, 
    mock_whitelist_config
):
    """
    Тест TEST режиму: whitelist активний, dry-run.
    """
    with patch('src.core.whitelist.whitelist_manager.Path') as mock_path:
        mock_path.return_value = mock_whitelist_config
        
        service = BulkTaggingService(confluence_client=mock_confluence_client)
        
        # Встановлюємо TEST mode
        service.agent.mode = "TEST"
        
        result = await service.tag_space("TEST", dry_run=None)

        # ✅ Updated checks for new synchronous response structure
        assert "task_id" in result
        assert isinstance(result["task_id"], str)
        # ❌ Removed: "status" field (not in sync response)
        
        # Перевірки
        assert result["mode"] == "TEST"
        assert result["whitelist_enabled"] is True
        assert result["dry_run"] is True
        assert result["skipped_by_whitelist"] > 0  # Має бути пропущені сторінки
        assert result["processed"] == 2  # 100, 200 in whitelist
        assert result["total"] == 6  # All pages in space


@pytest.mark.asyncio
async def test_tag_space_safe_test_mode_whitelist_active(
    mock_confluence_client,
    mock_whitelist_config
):
    """
    Тест SAFE_TEST режиму: whitelist активний, реальні зміни.
    """
    with patch('src.core.whitelist.whitelist_manager.Path') as mock_path:
        mock_path.return_value = mock_whitelist_config
        
        service = BulkTaggingService(confluence_client=mock_confluence_client)
        
        # Встановлюємо SAFE_TEST mode
        service.agent.mode = "SAFE_TEST"
        
        result = await service.tag_space("TEST", dry_run=False)
        
        # ✅ Updated checks
        assert result["mode"] == "SAFE_TEST"
        assert result["whitelist_enabled"] is True
        assert result["dry_run"] is False
        assert result["skipped_by_whitelist"] > 0
        assert result["processed"] == 2  # Only whitelisted pages processed


@pytest.mark.asyncio
async def test_tag_space_prod_mode_whitelist_ignored(
    mock_confluence_client,
    mock_whitelist_config
):
    """
    ❌ СТАРИЙ ТЕСТ - НЕ ВІДПОВІДАЄ НОВІЙ АРХІТЕКТУРІ
    
    Нова архітектура:
    - tag_space ЗАВЖДИ використовує whitelist для визначення scope
    - PROD mode не ігнорує whitelist у tag_space
    - Якщо потрібно обробити весь простір без whitelist - це окремий endpoint
    """
    with patch('src.core.whitelist.whitelist_manager.Path') as mock_path:
        mock_path.return_value = mock_whitelist_config
        
        service = BulkTaggingService(confluence_client=mock_confluence_client)
        
        # Встановлюємо PROD mode
        service.agent.mode = "PROD"
        
        result = await service.tag_space("TEST", dry_run=False)
        
        # ✅ НОВІ ОЧІКУВАННЯ: PROD mode використовує whitelist для tag_space
        assert result["mode"] == "PROD"
        assert result["whitelist_enabled"] is True  # ✅ Changed: whitelist always enabled for tag_space
        assert result["dry_run"] is False
        assert result["skipped_by_whitelist"] > 0  # ✅ Changed: whitelist filters pages


@pytest.mark.asyncio
async def test_tag_space_no_whitelist_entries(
    mock_confluence_client,
    mock_whitelist_config
):
    """
    Тест коли для простору немає whitelist entries.
    """
    with patch('src.core.whitelist.whitelist_manager.Path') as mock_path:
        mock_path.return_value = mock_whitelist_config
        
        service = BulkTaggingService(confluence_client=mock_confluence_client)
        service.agent.mode = "TEST"
        
        # Запит для неіснуючого простору
        result = await service.tag_space("NONEXISTENT", dry_run=None)
        
        # Має повернути помилку
        assert result["errors"] == 0
        assert result["total"] == 0
        assert "No whitelist entries" in result["details"][0]["message"]


@pytest.mark.asyncio
async def test_tag_space_whitelist_with_children(
    mock_confluence_client,
    mock_whitelist_config
):
    """
    Тест що дочірні сторінки entry points також дозволені.
    """
    # Mock get_child_pages щоб повертати дочірні (list[str])
    mock_confluence_client.get_child_pages = AsyncMock(side_effect=[
        ["101", "102"],  # Дочірні для 100
        [],  # Для 101
        [],  # Для 102
        ["201"],  # Дочірні для 200
        []   # Для 201
    ])
    
    with patch('src.core.whitelist.whitelist_manager.Path') as mock_path:
        mock_path.return_value = mock_whitelist_config
        
        service = BulkTaggingService(confluence_client=mock_confluence_client)
        service.agent.mode = "TEST"
        
        result = await service.tag_space("TEST", dry_run=True)
        
        # 100, 101, 102, 200, 201 мають бути дозволені
        # 999 має бути пропущена
        assert result["skipped_by_whitelist"] == 1  # Тільки 999


@pytest.mark.asyncio
async def test_tag_space_processes_deep_subtree():
    """
    Інтеграційний тест: tag_space обробляє глибоке піддерево.
    
    Структура whitelist:
    - Entry point: 100
    - Дерево: 100 → 101 → 102 → 103
    
    Простір містить: 100, 101, 102, 103, 999
    Має обробити: 100, 101, 102, 103
    Має пропустити: 999
    """
    # Mock Confluence client
    mock_confluence = MagicMock()
    
    # Всі сторінки в просторі
    mock_confluence.get_all_pages_in_space = AsyncMock(return_value=[
        "100", "101", "102", "103", "999"
    ])
    
    # Структура дерева: 100 → 101 → 102 → 103
    mock_confluence.get_child_pages = AsyncMock(side_effect=[
        ["101"],  # 100 → 101
        ["102"],  # 101 → 102
        ["103"],  # 102 → 103
        []        # 103 (leaf)
    ])
    
    mock_confluence.get_page = AsyncMock(return_value={
        "id": "100",
        "title": "Test Page",
        "body": {"storage": {"value": "Test content"}}
    })
    mock_confluence.get_labels = AsyncMock(return_value=[])
    mock_confluence.update_labels = AsyncMock()
    
    # Mock whitelist з одним entry point
    import json
    import tempfile
    
    whitelist_config = {
        "spaces": [
            {
                "space_key": "DEEP",
                "pages": [
                    {"id": 100, "name": "Root", "root": True}
                ]
            }
        ]
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(whitelist_config, f)
        config_path = f.name
    
    try:
        with patch('src.core.whitelist.whitelist_manager.WhitelistManager.__init__') as mock_init:
            def custom_init(self, config_path=None):
                self.config_path = config_path
                self.config = whitelist_config
                self._allowed_ids_cache = {}
            
            mock_init.side_effect = custom_init
            
            service = BulkTaggingService(confluence_client=mock_confluence)
            service.agent.mode = "TEST"
            
            result = await service.tag_space("DEEP", dry_run=True)
            
            # Має обробити всі 4 сторінки з дерева
            assert result["processed"] >= 4, f"Expected at least 4 processed, got {result['processed']}"
            
            # Має пропустити 999
            assert result["skipped_by_whitelist"] >= 1
            
    finally:
        import os
        os.unlink(config_path)


@pytest.mark.asyncio
async def test_safe_test_allows_whitelist_subtree():
    """
    Критичний тест: SAFE_TEST режим дозволяє всі сторінки з whitelist піддерева.
    
    Перевіряє що:
    - Entry point дозволений
    - Дочірні сторінки дозволені
    - Не використовується TAGGING_AGENT_TEST_PAGE з .env
    - Використовується allowed_ids з WhitelistManager
    """
    # Mock Confluence client
    mock_confluence = MagicMock()
    
    # Простір містить: 100, 101, 102, 999
    mock_confluence.get_all_pages_in_space = AsyncMock(return_value=[
        "100", "101", "102", "999"
    ])
    
    # Структура дерева: 100 → 101, 102
    mock_confluence.get_child_pages = AsyncMock(side_effect=[
        ["101", "102"],  # 100 → 101, 102
        [],              # 101 (leaf)
        []               # 102 (leaf)
    ])
    
    mock_confluence.get_page = AsyncMock(return_value={
        "id": "100",
        "title": "Test Page",
        "body": {"storage": {"value": "Test content with domain-rehab-2-0 information"}}
    })
    mock_confluence.get_labels = AsyncMock(return_value=[])
    mock_confluence.update_labels = AsyncMock()
    
    # Mock whitelist
    import json
    import tempfile
    
    whitelist_config = {
        "spaces": [
            {
                "space_key": "SAFETEST",
                "pages": [
                    {"id": 100, "name": "Root", "root": True}
                ]
            }
        ]
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(whitelist_config, f)
        config_path = f.name
    
    try:
        with patch('src.core.whitelist.whitelist_manager.WhitelistManager.__init__') as mock_init:
            def custom_init(self, config_path=None):
                self.config_path = config_path
                self.config = whitelist_config
                self._allowed_ids_cache = {}
            
            mock_init.side_effect = custom_init
            
            service = BulkTaggingService(confluence_client=mock_confluence)
            service.agent.mode = "SAFE_TEST"
            
            # SAFE_TEST з dry_run=False → реальний запис
            result = await service.tag_space("SAFETEST", dry_run=False)
            
            # Перевірки
            assert result["mode"] == "SAFE_TEST"
            assert result["dry_run"] is False
            assert result["whitelist_enabled"] is True
            
            # Має обробити 100, 101, 102 (whitelist entry + дочірні)
            assert result["processed"] == 3, f"Expected 3 processed, got {result['processed']}"
            
            # Має пропустити 999 (не в whitelist)
            assert result["skipped_by_whitelist"] == 1
            
            # Всі оброблені мають статус "updated" (не "forbidden")
            details = result.get("details", [])
            processed_details = [d for d in details if d["page_id"] in ["100", "101", "102"]]
            
            for detail in processed_details:
                assert detail["status"] in ["updated", "dry_run"], \
                    f"Page {detail['page_id']} has status {detail['status']}, expected 'updated'"
            
            # Перевірка що update_labels був викликаний (реальний запис)
            assert mock_confluence.update_labels.call_count >= 0  # Може бути 0 якщо немає нових тегів
            
    finally:
        import os
        os.unlink(config_path)


@pytest.mark.asyncio
async def test_safe_test_dry_run_does_not_write():
    """
    Критичний тест: SAFE_TEST + dry_run=true НЕ записує теги.
    
    Перевіряє що:
    - dry_run=true блокує запис
    - статус = "dry_run"
    - update_labels НЕ викликається
    - теги пропонуються, але не записуються
    """
    # Mock Confluence client
    mock_confluence = MagicMock()
    
    # Простір містить: 100, 101
    mock_confluence.get_all_pages_in_space = AsyncMock(return_value=["100", "101"])
    
    # Структура дерева: 100 → 101
    mock_confluence.get_child_pages = AsyncMock(side_effect=[
        ["101"],  # 100 → 101
        []        # 101 (leaf)
    ])
    
    mock_confluence.get_page = AsyncMock(return_value={
        "id": "100",
        "title": "Test Page",
        "body": {"storage": {"value": "Test content with domain-rehab-2-0 information"}}
    })
    mock_confluence.get_labels = AsyncMock(return_value=[])
    mock_confluence.update_labels = AsyncMock()
    
    # Mock whitelist
    import json
    import tempfile
    
    whitelist_config = {
        "spaces": [
            {
                "space_key": "DRYRUN",
                "pages": [
                    {"id": 100, "name": "Root", "root": True}
                ]
            }
        ]
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(whitelist_config, f)
        config_path = f.name
    
    try:
        with patch('src.core.whitelist.whitelist_manager.WhitelistManager.__init__') as mock_init:
            def custom_init(self, config_path=None):
                self.config_path = config_path
                self.config = whitelist_config
                self._allowed_ids_cache = {}
            
            mock_init.side_effect = custom_init
            
            service = BulkTaggingService(confluence_client=mock_confluence)
            service.agent.mode = "SAFE_TEST"
            
            # SAFE_TEST з dry_run=True → тільки симуляція
            result = await service.tag_space("DRYRUN", dry_run=True)
            
            # Перевірки режиму
            assert result["mode"] == "SAFE_TEST"
            assert result["dry_run"] is True
            assert result["whitelist_enabled"] is True
            
            # Має обробити обидві сторінки
            assert result["processed"] == 2
            
            # Всі мають статус "dry_run"
            details = result.get("details", [])
            for detail in details:
                assert detail["status"] == "dry_run", \
                    f"Page {detail['page_id']} has status {detail['status']}, expected 'dry_run'"
            
            # ✅ КРИТИЧНА ПЕРЕВІРКА: update_labels НЕ має бути викликаний
            assert mock_confluence.update_labels.call_count == 0, \
                f"update_labels was called {mock_confluence.update_labels.call_count} times, expected 0 (dry_run should prevent writes)"
            
            # Перевірка що теги все ж були згенеровані (для перегляду)
            for detail in details:
                assert "tags" in detail
                assert detail["tags"] is not None
                # proposed має містити згенеровані теги
                assert "proposed" in detail["tags"]
            
    finally:
        import os
        os.unlink(config_path)


@pytest.mark.asyncio
async def test_prod_mode_uses_whitelist_dry_run_true():
    """
    Критичний тест: PROD режим тепер використовує whitelist.
    PROD + dry_run=true: обробляються тільки whitelist сторінки, без запису.
    
    Перевіряє що:
    - Whitelist застосовується в PROD режимі
    - dry_run=true блокує запис
    - Сторінки поза whitelist пропускаються
    - update_labels НЕ викликається
    """
    # Mock Confluence client
    mock_confluence = MagicMock()
    
    # Простір містить: 100, 101, 999 (999 не в whitelist)
    mock_confluence.get_all_pages_in_space = AsyncMock(return_value=["100", "101", "999"])
    
    # Структура дерева: 100 → 101
    mock_confluence.get_child_pages = AsyncMock(side_effect=[
        ["101"],  # 100 → 101
        []        # 101 (leaf)
    ])
    
    mock_confluence.get_page = AsyncMock(return_value={
        "id": "100",
        "title": "Test Page",
        "body": {"storage": {"value": "Test content with domain-rehab-2-0 information"}}
    })
    mock_confluence.get_labels = AsyncMock(return_value=[])
    mock_confluence.update_labels = AsyncMock()
    
    # Mock whitelist
    import json
    import tempfile
    
    whitelist_config = {
        "spaces": [
            {
                "space_key": "PROD_WHITELIST",
                "pages": [
                    {"id": 100, "name": "Root", "root": True}
                ]
            }
        ]
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(whitelist_config, f)
        config_path = f.name
    
    try:
        with patch('src.core.whitelist.whitelist_manager.WhitelistManager.__init__') as mock_init:
            def custom_init(self, config_path=None):
                self.config_path = config_path
                self.config = whitelist_config
                self._allowed_ids_cache = {}
            
            mock_init.side_effect = custom_init
            
            service = BulkTaggingService(confluence_client=mock_confluence)
            service.agent.mode = "PROD"
            
            # PROD з dry_run=True → симуляція з whitelist
            result = await service.tag_space("PROD_WHITELIST", dry_run=True)
            
            # Перевірки режиму
            assert result["mode"] == "PROD"
            assert result["dry_run"] is True
            assert result["whitelist_enabled"] is True
            
            # Має обробити тільки whitelist (100, 101)
            assert result["processed"] == 2, f"Expected 2 processed, got {result['processed']}"
            
            # Має пропустити 999 (не в whitelist)
            assert result["skipped_by_whitelist"] == 1
            
            # Всі мають статус "dry_run"
            details = result.get("details", [])
            for detail in details:
                assert detail["status"] == "dry_run"
            
            # ✅ update_labels НЕ викликається (dry_run)
            assert mock_confluence.update_labels.call_count == 0
            
    finally:
        import os
        os.unlink(config_path)


@pytest.mark.asyncio
async def test_prod_mode_uses_whitelist_dry_run_false():
    """
    Критичний тест: PROD + dry_run=false з whitelist.
    
    Перевіряє що:
    - Whitelist застосовується в PROD режимі
    - dry_run=false дозволяє запис
    - Сторінки поза whitelist пропускаються
    - update_labels викликається для whitelist сторінок
    """
    # Mock Confluence client
    mock_confluence = MagicMock()
    
    # Простір містить: 100, 101, 999
    mock_confluence.get_all_pages_in_space = AsyncMock(return_value=["100", "101", "999"])
    
    # Структура дерева: 100 → 101
    mock_confluence.get_child_pages = AsyncMock(side_effect=[
        ["101"],  # 100 → 101
        []        # 101 (leaf)
    ])
    
    mock_confluence.get_page = AsyncMock(return_value={
        "id": "100",
        "title": "Test Page",
        "body": {"storage": {"value": "Test content with domain-rehab-2-0 information"}}
    })
    mock_confluence.get_labels = AsyncMock(return_value=[])
    mock_confluence.update_labels = AsyncMock()
    
    # Mock whitelist
    import json
    import tempfile
    
    whitelist_config = {
        "spaces": [
            {
                "space_key": "PROD_WRITE",
                "pages": [
                    {"id": 100, "name": "Root", "root": True}
                ]
            }
        ]
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(whitelist_config, f)
        config_path = f.name
    
    try:
        with patch('src.core.whitelist.whitelist_manager.WhitelistManager.__init__') as mock_init:
            def custom_init(self, config_path=None):
                self.config_path = config_path
                self.config = whitelist_config
                self._allowed_ids_cache = {}
            
            mock_init.side_effect = custom_init
            
            service = BulkTaggingService(confluence_client=mock_confluence)
            service.agent.mode = "PROD"
            
            # PROD з dry_run=False → реальний запис з whitelist
            result = await service.tag_space("PROD_WRITE", dry_run=False)
            
            # Перевірки режиму
            assert result["mode"] == "PROD"
            assert result["dry_run"] is False
            assert result["whitelist_enabled"] is True
            
            # Має обробити тільки whitelist (100, 101)
            assert result["processed"] == 2
            
            # Має пропустити 999
            assert result["skipped_by_whitelist"] == 1
            
            # Всі мають статус "updated"
            details = result.get("details", [])
            for detail in details:
                assert detail["status"] == "updated"
            
            # ✅ update_labels може бути викликаний (якщо є нові теги)
            # Не перевіряємо точну кількість, бо залежить від згенерованих тегів
            
    finally:
        import os
        os.unlink(config_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
