"""
Тести для перевірки dry_run логіки в tag-tree для різних режимів.
Перевіряє що TEST завжди dry-run, а SAFE_TEST і PROD працюють правильно.
"""

import pytest
import json
import tempfile
import os
from unittest.mock import AsyncMock, MagicMock, patch
from src.services.bulk_tagging_service import BulkTaggingService


@pytest.fixture
def mock_confluence():
    """Mock Confluence client."""
    mock = MagicMock()
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
def whitelist_config():
    """Create temporary whitelist config."""
    config = {
        "spaces": [
            {
                "space_key": "TEST_SPACE",
                "pages": [
                    {"id": 100, "name": "Root", "root": True}
                ]
            }
        ]
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(config, f)
        config_path = f.name
    
    yield config_path
    
    os.unlink(config_path)


@pytest.mark.asyncio
async def test_tag_tree_test_mode_forces_dry_run(mock_confluence, whitelist_config):
    """
    TEST режим завжди має dry_run=True, навіть якщо передано dry_run=False.
    """
    with patch('src.core.whitelist.whitelist_manager.Path') as mock_path:
        mock_path.return_value = whitelist_config
        
        with patch('src.sections.section_detector.detect_section') as mock_detect:
            mock_detect.return_value = "test-section"
            
            with patch('src.sections.whitelist.get_allowed_labels') as mock_labels:
                mock_labels.return_value = ["test-tag"]
                
                service = BulkTaggingService(confluence_client=mock_confluence)
                service.agent.mode = "TEST"
                
                # Передаємо dry_run=False, але TEST має примусити True
                result = await service.tag_tree("100", space_key="TEST_SPACE", dry_run=False)
                
                # Перевірки
                assert result["mode"] == "TEST"
                assert result["dry_run"] is True, "TEST mode must force dry_run=True"
                assert mock_confluence.update_labels.call_count == 0, "TEST mode must not write to Confluence"
                
                # Всі details мають статус dry_run
                if result["details"]:
                    for detail in result["details"]:
                        assert detail["status"] in ["dry_run", "no_changes"], \
                            f"TEST mode: expected dry_run or no_changes, got {detail['status']}"


@pytest.mark.asyncio
async def test_tag_tree_safe_test_mode_dry_run_true(mock_confluence, whitelist_config):
    """
    SAFE_TEST режим з dry_run=True → симуляція, без запису.
    """
    with patch('src.core.whitelist.whitelist_manager.Path') as mock_path:
        mock_path.return_value = whitelist_config
        
        with patch('src.sections.section_detector.detect_section') as mock_detect:
            mock_detect.return_value = "test-section"
            
            with patch('src.sections.whitelist.get_allowed_labels') as mock_labels:
                mock_labels.return_value = ["test-tag"]
                
                service = BulkTaggingService(confluence_client=mock_confluence)
                service.agent.mode = "SAFE_TEST"
                
                result = await service.tag_tree("100", space_key="TEST_SPACE", dry_run=True)
                
                # Перевірки
                assert result["mode"] == "SAFE_TEST"
                assert result["dry_run"] is True
                assert mock_confluence.update_labels.call_count == 0, "dry_run=True must not write"


@pytest.mark.asyncio
async def test_tag_tree_safe_test_mode_dry_run_false(mock_confluence, whitelist_config):
    """
    SAFE_TEST режим з dry_run=False → реальний запис дозволений.
    """
    with patch('src.core.whitelist.whitelist_manager.Path') as mock_path:
        mock_path.return_value = whitelist_config
        
        with patch('src.sections.section_detector.detect_section') as mock_detect:
            mock_detect.return_value = "test-section"
            
            with patch('src.sections.whitelist.get_allowed_labels') as mock_labels:
                mock_labels.return_value = ["test-tag"]
                
                service = BulkTaggingService(confluence_client=mock_confluence)
                service.agent.mode = "SAFE_TEST"
                
                result = await service.tag_tree("100", space_key="TEST_SPACE", dry_run=False)
                
                # Перевірки
                assert result["mode"] == "SAFE_TEST"
                assert result["dry_run"] is False
                # update_labels може бути викликаний якщо є нові теги


@pytest.mark.asyncio
async def test_tag_tree_prod_mode_dry_run_true(mock_confluence, whitelist_config):
    """
    PROD режим з dry_run=True → симуляція.
    """
    with patch('src.core.whitelist.whitelist_manager.Path') as mock_path:
        mock_path.return_value = whitelist_config
        
        with patch('src.sections.section_detector.detect_section_safe') as mock_detect:
            mock_detect.return_value = "test-section"
            
            with patch('src.sections.whitelist.get_allowed_labels') as mock_labels:
                mock_labels.return_value = ["test-tag"]
                
                service = BulkTaggingService(confluence_client=mock_confluence)
                service.agent.mode = "PROD"
                
                result = await service.tag_tree("100", space_key="TEST_SPACE", dry_run=True)
                
                # Перевірки
                assert result["mode"] == "PROD"
                assert result["dry_run"] is True
                assert mock_confluence.update_labels.call_count == 0


@pytest.mark.asyncio
async def test_tag_tree_prod_mode_dry_run_false(mock_confluence, whitelist_config):
    """
    PROD режим з dry_run=False → реальний запис дозволений.
    """
    with patch('src.core.whitelist.whitelist_manager.Path') as mock_path:
        mock_path.return_value = whitelist_config
        
        with patch('src.sections.section_detector.detect_section_safe') as mock_detect:
            mock_detect.return_value = "test-section"
            
            with patch('src.sections.whitelist.get_allowed_labels') as mock_labels:
                mock_labels.return_value = ["test-tag"]
                
                service = BulkTaggingService(confluence_client=mock_confluence)
                service.agent.mode = "PROD"
                
                result = await service.tag_tree("100", space_key="TEST_SPACE", dry_run=False)
                
                # Перевірки
                assert result["mode"] == "PROD"
                assert result["dry_run"] is False
                # update_labels може бути викликаний


@pytest.mark.asyncio
async def test_tag_tree_test_mode_with_none_dry_run(mock_confluence, whitelist_config):
    """
    TEST режим з dry_run=None → має примусити True.
    """
    with patch('src.core.whitelist.whitelist_manager.Path') as mock_path:
        mock_path.return_value = whitelist_config
        
        with patch('src.sections.section_detector.detect_section') as mock_detect:
            mock_detect.return_value = "test-section"
            
            with patch('src.sections.whitelist.get_allowed_labels') as mock_labels:
                mock_labels.return_value = ["test-tag"]
                
                service = BulkTaggingService(confluence_client=mock_confluence)
                service.agent.mode = "TEST"
                
                result = await service.tag_tree("100", space_key="TEST_SPACE", dry_run=None)
                
                # Перевірки
                assert result["dry_run"] is True
                assert mock_confluence.update_labels.call_count == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
