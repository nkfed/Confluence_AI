import os
import pytest
from src.services.tagging_context import clean_html_for_ai, html_to_text_limited, prepare_ai_context


def test_html_cleaning_removes_noise():
    html = """
    <script>alert('x')</script>
    <style>.a{}</style>
    <ac:macro>macro</ac:macro>
    <p data-id="1">Keep me</p>
    """
    cleaned = clean_html_for_ai(html)
    assert "script" not in cleaned.lower()
    assert "style" not in cleaned.lower()
    assert "ac:macro" not in cleaned.lower()
    assert "Keep me" in cleaned


def test_text_limiting_defaults_to_env(monkeypatch):
    monkeypatch.setenv("TAGGING_MAX_CONTEXT_CHARS", "20")
    from importlib import reload
    import settings
    reload(settings)
    from src.services import tagging_context
    reload(tagging_context)

    long_html = "<p>1234567890</p>" * 5
    text = tagging_context.html_to_text_limited(long_html)
    assert len(text) <= 20


def test_prepare_ai_context_trims(monkeypatch):
    monkeypatch.setenv("TAGGING_MAX_CONTEXT_CHARS", "15")
    from importlib import reload
    import settings
    reload(settings)
    from src.services import tagging_context
    reload(tagging_context)

    html = "<p>ABCDEFGHIJ</p><p>KLMNOP</p>"
    text = tagging_context.prepare_ai_context(html)
    assert len(text) <= 15
    assert "A" in text
