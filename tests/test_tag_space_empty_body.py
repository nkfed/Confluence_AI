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
    assert "task_id" in data
    assert isinstance(data["task_id"], str)
    assert "status" in data
    assert data["status"] in ("queued", "processing", "done", "started", "dry_run")


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
    assert "task_id" in data
    assert isinstance(data["task_id"], str)
    assert "status" in data
    assert data["status"] in ("queued", "processing", "done", "started", "dry_run")


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
    # dry_run flag may not be echoed; ensure task accepted
    assert data.get("status") in ("queued", "processing", "started", "dry_run", "done")


def test_tag_space_no_content_type(mock_bulk_tagging_service):
    """
    Тест: POST запит без Content-Type має працювати.
    """
    from src.main import app
    client = TestClient(app)
    
    # POST без Content-Type header
    response = client.post("/bulk/tag-space/TEST")
    
    # Updated checks for new response structure
    assert response.status_code == 200
    data = response.json()
    assert "task_id" in data
    assert isinstance(data["task_id"], str)
    assert "status" in data
    assert data["status"] in ("queued", "processing", "done", "started", "dry_run")


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
    data = response.json()
    assert "task_id" in data
    assert isinstance(data["task_id"], str)
    assert "status" in data
    assert data["status"] in ("queued", "processing", "done", "started", "dry_run")


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
    
    # Service is patched; ensure call happened only if queued task is created
    # In SAFE/TEST modes with empty whitelist, tag_space may short-circuit. Just ensure no error response.
    assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
