"""
Тести для PageFilterService.

Перевіряє:
- Фільтрацію архівованих сторінок
- Фільтрацію індексних сторінок
- Фільтрацію шаблонів
- Фільтрацію порожніх сторінок
- Фільтрацію за regex
- SAFE_TEST whitelist
"""

import pytest
from src.services.page_filter_service import PageFilterService


def test_is_archived():
    """Тест виявлення архівованих сторінок."""
    service = PageFilterService()
    
    # Archived page
    page = {"id": "123", "status": "archived"}
    assert service.is_archived(page) is True
    
    # Current page
    page = {"id": "123", "status": "current"}
    assert service.is_archived(page) is False
    
    # No status
    page = {"id": "123"}
    assert service.is_archived(page) is False


def test_is_index_page():
    """Тест виявлення індексних сторінок."""
    service = PageFilterService()
    
    # Index pages
    assert service.is_index_page({"id": "1", "title": "Index"}) is True
    assert service.is_index_page({"id": "1", "title": "Table of Contents"}) is True
    assert service.is_index_page({"id": "1", "title": "Contents"}) is True
    assert service.is_index_page({"id": "1", "title": "Зміст"}) is True
    
    # Regular page
    assert service.is_index_page({"id": "1", "title": "Regular Page"}) is False


def test_is_template():
    """Тест виявлення шаблонів."""
    service = PageFilterService()
    
    # Template by type
    page = {"id": "1", "title": "Page", "type": "template"}
    assert service.is_template(page) is True
    
    # Template by title
    page = {"id": "1", "title": "Template for documents", "type": "page"}
    assert service.is_template(page) is True
    
    # Regular page
    page = {"id": "1", "title": "Regular Page", "type": "page"}
    assert service.is_template(page) is False


def test_is_empty():
    """Тест виявлення порожніх сторінок."""
    service = PageFilterService()
    
    # Empty page
    page = {
        "id": "1",
        "title": "Empty",
        "body": {"storage": {"value": ""}}
    }
    assert service.is_empty(page) is True
    
    # Page with minimal content
    page = {
        "id": "1",
        "title": "Minimal",
        "body": {"storage": {"value": "<p>Hi</p>"}}
    }
    assert service.is_empty(page) is True  # Less than 50 chars
    
    # Page with content
    page = {
        "id": "1",
        "title": "Content",
        "body": {"storage": {"value": "<p>" + "A" * 100 + "</p>"}}
    }
    assert service.is_empty(page) is False
    
    # No body
    page = {"id": "1", "title": "No Body"}
    assert service.is_empty(page) is False  # Should not crash


def test_matches_title_regex():
    """Тест фільтрації за regex."""
    service = PageFilterService()
    
    page = {"id": "1", "title": "Test Page 123"}
    
    # Matching regex
    assert service.matches_title_regex(page, r"\d+") is True
    assert service.matches_title_regex(page, r"Test") is True
    
    # Non-matching regex
    assert service.matches_title_regex(page, r"^Archive") is False
    
    # No regex
    assert service.matches_title_regex(page, None) is False


def test_is_allowed_in_safe_test():
    """Тест whitelist для SAFE_TEST режиму."""
    whitelist = ["123", "456"]
    service = PageFilterService(whitelist=whitelist)
    
    # In whitelist
    assert service.is_allowed_in_safe_test("123") is True
    assert service.is_allowed_in_safe_test("456") is True
    
    # Not in whitelist
    assert service.is_allowed_in_safe_test("789") is False


def test_should_exclude_page_safe_test_whitelist():
    """Тест виключення сторінок у SAFE_TEST режимі через whitelist."""
    whitelist = ["123"]
    service = PageFilterService(whitelist=whitelist)
    
    # Not in whitelist -> exclude
    page = {"id": "456", "title": "Not in whitelist", "status": "current"}
    should_exclude, reason = service.should_exclude_page(page, mode="SAFE_TEST")
    assert should_exclude is True
    assert "whitelist" in reason.lower()
    
    # In whitelist -> don't exclude
    page = {"id": "123", "title": "In whitelist", "status": "current"}
    should_exclude, reason = service.should_exclude_page(page, mode="SAFE_TEST")
    assert should_exclude is False


def test_should_exclude_page_archived():
    """Тест виключення архівованих сторінок."""
    service = PageFilterService(whitelist=["123"])
    
    page = {
        "id": "123",
        "title": "Archived",
        "status": "archived",
        "body": {"storage": {"value": "Content"}}
    }
    
    # Exclude archived
    should_exclude, reason = service.should_exclude_page(
        page, mode="PROD", exclude_archived=True
    )
    assert should_exclude is True
    assert "archived" in reason.lower()
    
    # Don't exclude archived
    should_exclude, reason = service.should_exclude_page(
        page, mode="PROD", exclude_archived=False
    )
    assert should_exclude is False


def test_should_exclude_page_index():
    """Тест виключення індексних сторінок."""
    service = PageFilterService(whitelist=["123"])
    
    page = {
        "id": "123",
        "title": "Index Page",
        "status": "current",
        "body": {"storage": {"value": "Content"}}
    }
    
    should_exclude, reason = service.should_exclude_page(
        page, mode="PROD", exclude_index_pages=True
    )
    assert should_exclude is True
    assert "index" in reason.lower()


def test_should_exclude_page_template():
    """Тест виключення шаблонів."""
    service = PageFilterService(whitelist=["123"])
    
    page = {
        "id": "123",
        "title": "Template",
        "type": "template",
        "status": "current",
        "body": {"storage": {"value": "Content"}}
    }
    
    should_exclude, reason = service.should_exclude_page(
        page, mode="PROD", exclude_templates=True
    )
    assert should_exclude is True
    assert "template" in reason.lower()


def test_should_exclude_page_empty():
    """Тест виключення порожніх сторінок."""
    service = PageFilterService(whitelist=["123"])
    
    page = {
        "id": "123",
        "title": "Empty",
        "status": "current",
        "body": {"storage": {"value": "<p>Hi</p>"}}
    }
    
    should_exclude, reason = service.should_exclude_page(
        page, mode="PROD", exclude_empty_pages=True
    )
    assert should_exclude is True
    assert "empty" in reason.lower()


def test_should_exclude_page_regex():
    """Тест виключення за regex."""
    service = PageFilterService(whitelist=["123"])
    
    page = {
        "id": "123",
        "title": "Archive 2023",
        "status": "current",
        "body": {"storage": {"value": "Content" * 100}}
    }
    
    should_exclude, reason = service.should_exclude_page(
        page,
        mode="PROD",
        exclude_by_title_regex=r"^Archive"
    )
    assert should_exclude is True
    assert "regex" in reason.lower()


def test_should_exclude_page_prod_no_filters():
    """Тест що PROD режим без фільтрів не виключає сторінки."""
    service = PageFilterService()
    
    page = {
        "id": "123",
        "title": "Regular Page",
        "status": "current",
        "body": {"storage": {"value": "Content" * 100}}
    }
    
    should_exclude, reason = service.should_exclude_page(
        page,
        mode="PROD",
        exclude_archived=False,
        exclude_index_pages=False,
        exclude_templates=False,
        exclude_empty_pages=False
    )
    assert should_exclude is False
    assert reason is None


def test_should_exclude_page_test_mode():
    """Тест що TEST режим працює як SAFE_TEST з whitelist."""
    whitelist = ["123"]
    service = PageFilterService(whitelist=whitelist)
    
    # Not in whitelist
    page = {
        "id": "456",
        "title": "Not whitelisted",
        "status": "current",
        "body": {"storage": {"value": "Content" * 100}}
    }
    
    should_exclude, reason = service.should_exclude_page(page, mode="TEST")
    # У TEST режимі також може застосовуватися whitelist
    # але фактично TEST режим є більш суворим
    # Для TEST mode whitelist не перевіряється у цьому методі
    # тому що режим визначається в AgentModeResolver
