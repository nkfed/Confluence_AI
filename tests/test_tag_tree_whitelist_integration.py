"""
Інтеграційні тести для tag-tree з whitelist контролем.
"""

import pytest
import json
import tempfile
import os
from unittest.mock import AsyncMock, MagicMock, patch
from contextlib import contextmanager
from src.services.bulk_tagging_service import BulkTaggingService


@contextmanager
def mock_section_detection(section="domain-rehab-2-0"):
    """Helper для мокування section detection та allowed labels."""
    with patch('src.sections.section_detector.detect_section') as mock_detect:
        mock_detect.return_value = section
        with patch('src.sections.whitelist.get_allowed_labels') as mock_labels:
            mock_labels.return_value = ["domain-rehab-2-0", "doc-tech", "doc-user"]
            yield mock_detect, mock_labels


@pytest.mark.asyncio
async def test_tag_tree_root_in_whitelist():
    """
    Тест: root_page_id в whitelist → дерево обробляється.
    """
    mock_confluence = MagicMock()
    
    # Root page
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
    
    # Mock whitelist через Path
    whitelist_config = {
        "spaces": [
            {
                "space_key": "TREE_TEST",
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
        with patch('src.core.whitelist.whitelist_manager.Path') as mock_path:
            mock_path.return_value = config_path
            
            with mock_section_detection():
                service = BulkTaggingService(confluence_client=mock_confluence)
                service.agent.mode = "SAFE_TEST"
                
                result = await service.tag_tree("100", space_key="TREE_TEST", dry_run=True)
                
                # Перевірки
                assert result["status"] == "completed"
                assert result["whitelist_enabled"] is True
                assert result["space_key"] == "TREE_TEST"
                assert result["total"] == 3  # 100, 101, 102
                assert result["processed"] == 3
                assert result["skipped_by_whitelist"] == 0
            
    finally:
        os.unlink(config_path)


@pytest.mark.asyncio
async def test_tag_tree_root_not_in_whitelist():
    """
    Тест: root_page_id НЕ в whitelist → помилка.
    """
    mock_confluence = MagicMock()
    
    # Mock whitelist без root page
    whitelist_config = {
        "spaces": [
            {
                "space_key": "TREE_TEST",
                "pages": [
                    {"id": 200, "name": "Other Root", "root": True}
                ]
            }
        ]
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(whitelist_config, f)
        config_path = f.name
    
    try:
        with patch('src.core.whitelist.whitelist_manager.Path') as mock_path:
            mock_path.return_value = config_path
            
            with mock_section_detection():
                service = BulkTaggingService(confluence_client=mock_confluence)
                service.agent.mode = "SAFE_TEST"
                
                # 100 не в whitelist (тільки 200)
                result = await service.tag_tree("100", space_key="TREE_TEST", dry_run=True)
            
            # Перевірки
            assert result["status"] == "error"
            assert "not allowed by whitelist" in result["message"]
            assert result["total"] == 0
            assert result["processed"] == 0
            
    finally:
        os.unlink(config_path)


@pytest.mark.asyncio
async def test_tag_tree_safe_test_dry_run():
    """
    Тест: SAFE_TEST + dry_run=true → симуляція, без запису.
    """
    mock_confluence = MagicMock()
    
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
                "space_key": "SAFE_DRY",
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
        with patch('src.core.whitelist.whitelist_manager.Path') as mock_path:
            mock_path.return_value = config_path
            
            with mock_section_detection():
                service = BulkTaggingService(confluence_client=mock_confluence)
                service.agent.mode = "SAFE_TEST"
                
                result = await service.tag_tree("100", space_key="SAFE_DRY", dry_run=True)
            
            # Перевірки
            assert result["status"] == "completed"
            assert result["dry_run"] is True
            assert result["processed"] == 2  # 100, 101
            
            # ✅ update_labels НЕ викликається в dry_run
            assert mock_confluence.update_labels.call_count == 0
            
            # Всі details мають статус dry_run або no_changes
            for detail in result["details"]:
                assert detail["status"] in ["dry_run", "no_changes"]
            
    finally:
        os.unlink(config_path)


@pytest.mark.asyncio
async def test_tag_tree_safe_test_real_write():
    """
    Тест: SAFE_TEST + dry_run=false → реальний запис дозволений.
    """
    mock_confluence = MagicMock()
    
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
                "space_key": "SAFE_WRITE",
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
        with patch('src.core.whitelist.whitelist_manager.Path') as mock_path:
            mock_path.return_value = config_path
            
            with mock_section_detection():
                service = BulkTaggingService(confluence_client=mock_confluence)
                service.agent.mode = "SAFE_TEST"
                
                result = await service.tag_tree("100", space_key="SAFE_WRITE", dry_run=False)
            
            # Перевірки
            assert result["status"] == "completed"
            assert result["dry_run"] is False
            assert result["processed"] == 2
            
            # ✅ update_labels може бути викликаний (якщо є нові теги)
            # Не перевіряємо точну кількість, бо залежить від AI
            
    finally:
        os.unlink(config_path)


@pytest.mark.asyncio
async def test_tag_tree_prod_dry_run_uses_whitelist():
    """
    Тест: PROD + dry_run=true → whitelist застосовується.
    """
    mock_confluence = MagicMock()
    
    mock_confluence.get_child_pages = AsyncMock(side_effect=[
        ["101", "999"],  # 100 → 101, 999 (999 не в whitelist)
        []               # 101 (leaf)
    ])
    
    mock_confluence.get_page = AsyncMock(return_value={
        "id": "100",
        "title": "Test Page",
        "body": {"storage": {"value": "Test content"}}
    })
    mock_confluence.get_labels = AsyncMock(return_value=[])
    mock_confluence.update_labels = AsyncMock()
    
    # Mock whitelist
    import json
    import tempfile
    
    whitelist_config = {
        "spaces": [
            {
                "space_key": "PROD_DRY",
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
        with patch('src.core.whitelist.whitelist_manager.Path') as mock_path:
            mock_path.return_value = config_path
            
            with mock_section_detection():
                service = BulkTaggingService(confluence_client=mock_confluence)
                service.agent.mode = "PROD"
                
                result = await service.tag_tree("100", space_key="PROD_DRY", dry_run=True)
            
            # Перевірки
            assert result["status"] == "completed"
            assert result["whitelist_enabled"] is True
            assert result["total"] == 3  # 100, 101, 999
            assert result["processed"] == 2  # Тільки 100, 101 (999 filtered)
            assert result["skipped_by_whitelist"] == 1  # 999
            
            # ✅ update_labels НЕ викликається (dry_run)
            assert mock_confluence.update_labels.call_count == 0
            
    finally:
        os.unlink(config_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
