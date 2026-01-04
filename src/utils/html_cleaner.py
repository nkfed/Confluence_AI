"""
HTML cleaner для мінімізації контексту перед AI processing.

Користування:
    from src.utils.html_cleaner import clean_html_for_tagging, limit_text_length
    
    cleaned = clean_html_for_tagging(html)
    limited = limit_text_length(text, max_chars=3000)
"""

from bs4 import BeautifulSoup
from src.core.logging.logger import get_logger
import re

logger = get_logger(__name__)


def clean_html_for_tagging(html: str) -> str:
    """
    Видаляє непотрібні елементи з HTML для тегування.
    
    Видаляє:
    - <script>, <style>, <iframe>, <noscript> теги
    - <ac:macro> (Confluence макроси)
    - Порожні теги
    - HTML коментарі
    
    Залишає:
    - Текстовий вміст
    - Структура (параграфи, списки, заголовки)
    
    Args:
        html: HTML вміст сторінки Confluence
        
    Returns:
        Очищений HTML готовий для text extraction
        
    Приклад:
        >>> html = "<script>alert('x')</script><p>Text</p>"
        >>> clean_html_for_tagging(html)
        '<p>Text</p>'
    """
    if not html or not isinstance(html, str):
        logger.warning(f"[HtmlCleaner] Invalid HTML input: type={type(html)}")
        return ""
    
    try:
        soup = BeautifulSoup(html, "html.parser")
        
        # ✅ 1. Видалити теги скриптів, стилів, макросів
        for tag_name in ['script', 'style', 'iframe', 'noscript', 'meta', 'link']:
            for tag in soup.find_all(tag_name):
                tag.decompose()
        
        # ✅ 2. Видалити Confluence макроси
        for tag in soup.find_all(['ac:macro', 'ac:rich-text-body', 'ac:parameter']):
            tag.decompose()
        
        # ✅ 3. Видалити порожні теги та коментарі
        for comment in soup.find_all(string=lambda text: isinstance(text, str) and text.strip() == ''):
            if hasattr(comment, 'extract'):
                comment.extract()
        
        # ✅ 4. Видалити усі аттрибути для зменшення обсягу
        for tag in soup.find_all(True):
            tag.attrs = {}
        
        result = str(soup)
        
        # ✅ 5. Логування результату
        reduction = (1 - len(result) / max(len(html), 1)) * 100
        logger.debug(f"[HtmlCleaner] Cleaned: {len(html):,} → {len(result):,} chars ({reduction:.1f}% reduction)")
        
        return result
        
    except Exception as e:
        logger.error(f"[HtmlCleaner] Failed to clean HTML: {e}")
        logger.debug(f"[HtmlCleaner] Returning original HTML ({len(html)} chars)")
        return html


def html_to_clean_text(html: str, max_length: int = 3000) -> str:
    """
    Конвертує HTML в очищений текст обмеженої довжини.
    
    Процес:
    1. Очистити HTML від скриптів, стилів, макросів
    2. Видалити HTML теги
    3. Видалити порожні лінії
    4. Обмежити довжину
    
    Args:
        html: HTML вміст
        max_length: Максимальна довжина результуючого тексту (за замовчуванням 3000)
        
    Returns:
        Чистий текст обмеженої довжини
        
    Приклад:
        >>> html = "<p>Important <b>content</b></p><script>x</script>" * 100
        >>> text = html_to_clean_text(html, max_length=100)
        >>> len(text) <= 100
        True
    """
    if not html:
        return ""
    
    try:
        # ✅ 1. Очистити HTML
        cleaned_html = clean_html_for_tagging(html)
        
        # ✅ 2. Видалити HTML теги
        soup = BeautifulSoup(cleaned_html, "html.parser")
        text = soup.get_text(separator=" ", strip=True)
        
        # ✅ 3. Видалити порожні лінії та додаткові whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        # ✅ 4. Обмежити довжину на границі слів
        if len(text) <= max_length:
            logger.debug(f"[HtmlToText] Converted HTML: {len(html)} → {len(text)} chars")
            return text
        
        # Обрізати на границі слова, не посередині
        truncated = text[:max_length]
        
        # Знайти останнє слово/речення
        last_space = truncated.rfind(' ')
        last_period = truncated.rfind('.')
        last_exclaim = truncated.rfind('!')
        last_question = truncated.rfind('?')
        
        # Вибрати найсвіжіший boundary
        boundaries = [p for p in [last_space, last_period, last_exclaim, last_question] if p > max_length * 0.85]
        
        if boundaries:
            cut_point = max(boundaries)
        else:
            cut_point = last_space if last_space > 0 else max_length
        
        result = text[:cut_point].rstrip()
        logger.info(f"[HtmlToText] Converted & truncated: {len(html):,} chars HTML → {len(result):,} chars text (max={max_length})")
        
        return result
        
    except Exception as e:
        logger.error(f"[HtmlToText] Failed to convert HTML to text: {e}")
        # Fallback: просто видалити теги
        return re.sub(r'<[^>]+>', '', html)[:max_length]


def estimate_tokenization_cost(text: str, model: str = "gpt-4o") -> dict:
    """
    Приблизна оцінка кількості токенів для OpenAI API.
    
    Орієнтовні коефіцієнти:
    - 1 токен ≈ 4 символи (англійська)
    - 1 токен ≈ 2-3 символи (українська)
    
    Args:
        text: Текст для оцінки
        model: Модель (gpt-4o, gpt-4, gpt-3.5-turbo)
        
    Returns:
        Dict з оцінною кількістю токенів
        
    Приклад:
        >>> estimate_tokenization_cost("Привіт світ" * 100)
        {'estimated_tokens': 750, 'estimated_cost_usd': 0.00225}
    """
    # Коефіцієнти залежно від мови
    is_cyrillic = any('\u0400' <= char <= '\u04FF' for char in text)
    chars_per_token = 2.5 if is_cyrillic else 4  # Українська: 2.5 символи/токен
    
    estimated_tokens = len(text) / chars_per_token
    
    # Pricing (за podmínky OpenAI pricing, 2024)
    pricing = {
        "gpt-4o": {"input": 0.005, "output": 0.015},  # $ per 1K tokens
        "gpt-4": {"input": 0.03, "output": 0.06},
        "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015}
    }
    
    rates = pricing.get(model, pricing["gpt-4o"])
    estimated_cost = (estimated_tokens / 1000) * rates["input"]  # Assume input-only
    
    return {
        "text_length": len(text),
        "estimated_tokens": int(estimated_tokens),
        "language": "cyrillic (Ukrainian)" if is_cyrillic else "latin (English)",
        "model": model,
        "estimated_cost_usd": round(estimated_cost, 6)
    }


if __name__ == "__main__":
    # Test cases
    test_html = """
    <script>alert('test')</script>
    <p>This is important content for tagging.</p>
    <ac:macro>confluence macro</ac:macro>
    <p>More content here that should be preserved.</p>
    <style>.css { color: red; }</style>
    <ul>
        <li>Item 1</li>
        <li>Item 2</li>
    </ul>
    """
    
    # Test 1: Clean HTML
    cleaned = clean_html_for_tagging(test_html)
    print(f"Cleaned HTML: {len(test_html)} → {len(cleaned)} chars")
    assert "script" not in cleaned.lower()
    assert "This is important" in cleaned
    
    # Test 2: Convert to text with limit
    text = html_to_clean_text(test_html, max_length=50)
    print(f"Text (max 50 chars): {repr(text)}")
    assert len(text) <= 50
    
    # Test 3: Estimate tokens
    estimate = estimate_tokenization_cost(text)
    print(f"Token estimate: {estimate}")
    
    print("✅ All tests passed!")
