"""
Centralized AI context preparation for all tagging endpoints.
Scope: tag_pages, tag_tree, tag_space, auto_tag_page (and similar).
"""

from typing import Optional
from src.services.tag_pages_utils import clean_html_for_tag_pages
from src.utils.html_to_text import html_to_text
from src.core.logging.logger import get_logger
from settings import settings

logger = get_logger(__name__)


def clean_html_for_ai(html: Optional[str]) -> str:
    """Clean HTML using localized tag_pages cleaner (scripts/styles/macros removed)."""
    if not html or not isinstance(html, str):
        return ""
    return clean_html_for_tag_pages(html)


def html_to_text_limited(html: Optional[str]) -> str:
    """Convert HTML to text and limit length per TAGGING_MAX_CONTEXT_CHARS."""
    if not html:
        return ""
    text = html_to_text(clean_html_for_ai(html))
    max_len = settings.TAGGING_MAX_CONTEXT_CHARS
    if len(text) > max_len:
        text = text[:max_len].rstrip()
    return text


def prepare_ai_context(html: Optional[str]) -> str:
    """
    Clean HTML → text → trim to TAGGING_MAX_CONTEXT_CHARS with metrics logging.
    """
    if not html:
        return ""

    cleaned_html = clean_html_for_ai(html)
    text = html_to_text(cleaned_html)
    max_len = settings.TAGGING_MAX_CONTEXT_CHARS

    if len(text) > max_len:
        trimmed = text[:max_len].rstrip()
    else:
        trimmed = text

    logger.info(
        "[AIContext] original_html=%s chars, cleaned_text=%s chars, final=%s chars (limit=%s)",
        len(html), len(text), len(trimmed), max_len,
    )
    return trimmed
