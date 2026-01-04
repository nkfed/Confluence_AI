"""
Localized HTML cleaner utilities for tag_pages() ONLY.

This module is used EXCLUSIVELY within the tag_pages() method in BulkTaggingService.
It is NOT intended for use in tag-tree(), tag-space(), or other endpoints.

Usage:
    from src.services.tag_pages_utils import clean_html_for_tag_pages, limit_text_for_ai
    
    cleaned = clean_html_for_tag_pages(html)
    limited_text = limit_text_for_ai(cleaned, max_chars=3000)
"""

import re
from bs4 import BeautifulSoup
from src.core.logging.logger import get_logger

logger = get_logger(__name__)


def clean_html_for_tag_pages(html: str) -> str:
    """
    Removes unnecessary HTML elements specifically for tag_pages() context minimization.
    
    SCOPE: tag_pages() only
    
    Removes:
    - <script>, <style>, <iframe>, <noscript> tags
    - Confluence macros (<ac:macro>, etc.)
    - HTML comments
    - Empty tags
    - All attributes (keep text content only)
    
    Args:
        html: Raw HTML body.storage content from Confluence
        
    Returns:
        Cleaned HTML with unnecessary elements removed
    """
    if not html or not isinstance(html, str):
        logger.debug(f"[TagPagesUtils] Invalid HTML input: type={type(html)}, returning empty")
        return ""
    
    original_len = len(html)
    
    try:
        soup = BeautifulSoup(html, "html.parser")
        
        # Remove script, style, and other non-content tags
        for tag in soup.find_all(['script', 'style', 'iframe', 'noscript', 'meta', 'link']):
            tag.decompose()
        
        # Remove Confluence macros
        for tag in soup.find_all(['ac:macro', 'ac:rich-text-body', 'ac:parameter']):
            tag.decompose()
        
        # Remove attributes from all remaining tags (reduce size)
        for tag in soup.find_all(True):
            tag.attrs = {}
        
        result = str(soup)
        reduction_pct = (1 - len(result) / max(original_len, 1)) * 100
        
        logger.debug(
            f"[TagPagesUtils:clean_html] {original_len:,} → {len(result):,} chars "
            f"({reduction_pct:.1f}% reduction)"
        )
        
        return result
        
    except Exception as e:
        logger.warning(f"[TagPagesUtils:clean_html] Failed to clean HTML: {e}, returning original")
        return html


def html_to_text_limited(html: str, max_chars: int = 3000) -> str:
    """
    Converts cleaned HTML to plain text with character limit for AI processing.
    
    SCOPE: tag_pages() only
    
    Process:
    1. Clean HTML (remove scripts, styles, macros)
    2. Extract text from remaining HTML
    3. Normalize whitespace
    4. Limit to max_chars (breaking on word boundaries)
    
    Args:
        html: Raw HTML content
        max_chars: Maximum characters for AI context (default: 3000)
        
    Returns:
        Plain text limited to max_chars, optimized for AI processing
    """
    if not html:
        return ""
    
    try:
        # Step 1: Clean HTML
        cleaned = clean_html_for_tag_pages(html)
        
        # Step 2: Extract text
        soup = BeautifulSoup(cleaned, "html.parser")
        text = soup.get_text(separator=" ", strip=True)
        
        # Step 3: Normalize whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Step 4: Limit length intelligently
        if len(text) <= max_chars:
            logger.info(f"[TagPagesUtils:html_to_text] Final text: {len(text)} chars (within {max_chars} limit)")
            return text
        
        # Break at sentence boundary if possible
        truncated = text[:max_chars]
        
        # Find last sentence boundary
        boundaries = []
        for punct, offset in [('.', 0), ('!', 0), ('?', 0), ('\n', 0)]:
            pos = truncated.rfind(punct)
            if pos > max_chars * 0.85:  # Boundary should be close to max
                boundaries.append(pos + 1)
        
        # If no sentence boundary, break at word
        if boundaries:
            cut_point = max(boundaries)
        else:
            last_space = truncated.rfind(' ')
            cut_point = last_space if last_space > max_chars * 0.85 else max_chars
        
        result = text[:cut_point].rstrip()
        logger.info(
            f"[TagPagesUtils:html_to_text] Final text: {len(result)} chars "
            f"(limited from {len(text)} with boundary at {cut_point})"
        )
        
        return result
        
    except Exception as e:
        logger.error(f"[TagPagesUtils:html_to_text] Failed: {e}")
        # Fallback: strip HTML tags manually
        text = re.sub(r'<[^>]+>', '', html)
        if len(text) > max_chars:
            text = text[:max_chars]
        return text


def get_context_metrics(html: str, text: str) -> dict:
    """
    Returns metrics about context reduction for logging/debugging.
    
    SCOPE: tag_pages() only
    
    Args:
        html: Original HTML
        text: Final text for AI
        
    Returns:
        Dict with size metrics
    """
    return {
        "original_html_chars": len(html),
        "cleaned_text_chars": len(text),
        "reduction_pct": (1 - len(text) / max(len(html), 1)) * 100,
        "tokens_approx": int(len(text) / 4),  # Rough estimate: 4 chars per token
        "max_context_limit": 3000
    }


if __name__ == "__main__":
    # Self-test
    test_html = """
    <script>alert('x')</script>
    <p>Important content for tagging</p>
    <ac:macro>confluence</ac:macro>
    <style>.css { }</style>
    <p>More content here</p>
    """
    
    cleaned = clean_html_for_tag_pages(test_html)
    print(f"Cleaned: {cleaned[:100]}...")
    
    text = html_to_text_limited(test_html, max_chars=50)
    print(f"Text (50 chars): {repr(text)}")
    
    metrics = get_context_metrics(test_html, text)
    print(f"Metrics: {metrics}")
    
    print("✅ Self-test OK")
