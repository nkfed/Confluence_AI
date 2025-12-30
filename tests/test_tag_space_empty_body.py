"""
Тест для перевірки обробки порожнього тіла у tag-space ендпоінті.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def mock_bulk_tagging_service():
    """Mock BulkTaggingService."""
    with patch('src.api.routers.bulk.BulkTaggingService') as mock:
        service_instance = MagicMock()
        service_instance.tag_space = AsyncMock(return_value={
            "total": 10,
            "processed": 10,
            "success": 10,
            "errors": 0,
            "skipped_by_whitelist": 0,
            "dry_run": True,
            "mode": "TEST",
            "whitelist_enabled": True,
            "details": []
        })
        mock.return_value = service_instance
        yield service_instance


def test_tag_space_empty_body(mock_bulk_tagging_service):
    """
    Тест: POST запит без тіла має працювати.
    """
    from src.main import app
    client = TestClient(app)
    
    # POST без тіла (json=None означає що тіло не надсилається)
    response = client.post("/bulk/tag-space/TEST")
    
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "processed" in data


def test_tag_space_empty_json_object(mock_bulk_tagging_service):
    """
    Тест: POST запит з порожнім JSON об'єктом має працювати.
    """
    from src.main import app
    client = TestClient(app)
    
    # POST з порожнім JSON
    response = client.post("/bulk/tag-space/TEST", json={})
    
    assert response.status_code == 200
    data = response.json()
    assert "total" in data


def test_tag_space_with_query_params(mock_bulk_tagging_service):
    """
    Тест: POST запит з query параметрами (без тіла) має працювати.
    """
    from src.main import app
    client = TestClient(app)
    
    # POST з query параметрами
    response = client.post("/bulk/tag-space/TEST?dry_run=true")
    
    assert response.status_code == 200
    data = response.json()
    assert data["dry_run"] is True


def test_tag_space_no_content_type(mock_bulk_tagging_service):
    """
    Тест: POST запит без Content-Type має працювати.
    """
    from src.main import app
    client = TestClient(app)
    
    # POST без Content-Type header
    response = client.post("/bulk/tag-space/TEST")
    
    assert response.status_code == 200


def test_tag_space_with_null_body(mock_bulk_tagging_service):
    """
    Тест: POST запит з null в тілі має працювати або повернути помилку валідації.
    """
    from src.main import app
    client = TestClient(app)
    
    # POST з null (це валідний JSON)
    response = client.post("/bulk/tag-space/TEST", json=None)
    
    # Має працювати оскільки тіло необов'язкове
    assert response.status_code == 200


@pytest.mark.parametrize("space_key", [
    "TEST",
    "nkfedba",
    "~62e7af26f15eecaf500d44bc"
])
def test_tag_space_different_space_keys(mock_bulk_tagging_service, space_key):
    """
    Тест: різні формати space_key мають працювати.
    """
    from src.main import app
    client = TestClient(app)
    
    response = client.post(f"/bulk/tag-space/{space_key}")
    
    assert response.status_code == 200
    
    # Перевіряємо що service.tag_space був викликаний з правильним space_key
    mock_bulk_tagging_service.tag_space.assert_called()
    call_args = mock_bulk_tagging_service.tag_space.call_args
    assert call_args[0][0] == space_key


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
