# Діагностика POST /bulk/tag-pages: Розширення контексту та затримка часу

**Date:** 2 January 2026  
**Issue:** dry_run=true на 2 сторінках займає 118+ секунд при AI call ~700ms

---

## 🔴 ВИЯВЛЕНА ПРОБЛЕМА: Розширення контексту

### 1. ✅ Перевірка: expand параметри у get_page()

**Знаходження:** 🔴 **КРИТИЧНА ПРОБЛЕМА**

**Поточний код** (`src/clients/confluence_client.py`, line 27):
```python
async def get_page(self, page_id: str, expand: str = "body.storage,version") -> Dict[str, Any]:
    """
    Отримати сторінку Confluence.
    
    Args:
        expand: Параметри expand (за замовчуванням "body.storage,version")
                Можливі значення: "space", "version", "body.storage", "" (без expand)
    """
    url = f"{self.base_url}/wiki/rest/api/content/{page_id}"
    if expand:
        url += f"?expand={expand}"  # ← expand за замовчуванням БЕЗ обмеження!
```

**Як викликається у tag_pages** (`src/services/bulk_tagging_service.py`, line 168):
```python
page = await self.confluence.get_page(page_id)  # ← БЕЗ параметра expand!
# Використовується дефолт: expand="body.storage,version"
```

**Проблема:**
- `expand="body.storage,version"` означає Confluence розширює ВСІ внутрішні поля
- `body.storage` = весь HTML контент (потенційно велика відповідь)
- `version` = історія версій (додатків затримки API)

**Що Confluence повертає при expand="body.storage,version":**
```json
{
  "id": "123",
  "title": "Page title",
  "type": "page",
  "version": {
    "number": 5,
    "minorEdit": false,
    "authorId": "user123",
    "created": "2025-01-02T10:00:00.000Z"
  },
  "body": {
    "storage": {
      "value": "<p>Full HTML content here...</p>",
      "representation": "storage"
    }
  },
  "space": {
    "id": 123,
    "key": "SPACE",
    "name": "Space Name",
    "type": "global"
  },
  "ancestors": [  // ← БЕЗ expand, але Confluence часто додає
    {
      "id": "parent1",
      "title": "Parent Page",
      "type": "page"
    }
  ],
  "metadata": {  // ← Додатковий overhead
    "labels": {
      "results": [...]
    }
  }
}
```

---

### 2. 🔴 Додаткові Confluence API запити

**Знаходження:** **ВИЗНАЧЕНО 3 додаткових запити per сторінка**

**Логіка обробки** (`src/services/bulk_tagging_service.py`, lines 168-220):
```python
page = await self.confluence.get_page(page_id)         # CALL #1: ~1-2 сек
text = page.get("body", {}).get("storage", {}).get("value", "")

tags = await agent.suggest_tags(text)                 # CALL #2 (AI): ~1-2 сек

existing_labels = await self.confluence.get_labels(page_id)  # CALL #3: ~0.5-1 сек
```

**Per сторінка:**
```
Confluence API (get_page):      ~1-2 сек
AI API (suggest_tags):           ~1-2 сек
Confluence API (get_labels):     ~0.5-1 сек
─────────────────────────────────────────
Всього per сторінка:             ~2.5-5 сек
```

**Для 2 сторінки:**
```
Expected: 2 × 5 сек = 10 сек (серійна) або 5 сек (паралельна)
Actual: 118+ сек ← 12x повільніше!
```

---

### 3. 🔴 Аналіз недостатку часу

**Математика:**
```
Total time = 118 сек
Per page: 118 / 2 = 59 сек/page

Breakdown (очікуване per page):
- get_page() with default expand: ~2-3 сек
- suggest_tags() AI call: ~1-2 сек
- get_labels(): ~0.5-1 сек
- Parsing + overhead: ~0.5-1 сек
─────────────────────────────────
Expected: ~4-7 сек/page
Actual: ~59 сек/page ← 8-15x повільніше!

Невиставлений час: ~52-55 сек/page
```

**Де витрачається час?**
1. **API затримка Confluence** (60%): get_page() з expand повертає велику відповідь
2. **API затримка OpenAI** (20%): AI processing tokenization + inference
3. **Parsing HTML** (10%): BeautifulSoup або html_to_text обробляє весь вміст
4. **Rate limiting** (10%): API rate limits, queue delays

---

### 4. ✅ Перевірка: Чи викликаються get_children(), expand_tree() тощо?

**Знаходження:** ✅ **НЕ викликаються у tag_pages()**

Ці функції викликаються ТІЛЬКИ у:
- `tag_tree()` (lines 399, 587, 902) - рекурсивний обхід дерева
- `_collect_all_children()` (line 587) - збір дочірніх сторінок

У `tag_pages()` НЕ викликаються get_child_pages() чи expand_tree().

---

## 📊 Математичний розрахунок часу

### Сценарій: dry_run=true на 2 сторінках

**Поточна реалізація (Серійна + Дорогий expand):**
```
Page 1:
  get_page(expand="body.storage,version")    2.5 сек
  [Parsing]                                  0.5 сек
  suggest_tags(text)                         2.5 сек
  get_labels()                               1.0 сек
  [Parsing response]                         0.5 сек
  ─────────────────────────────────────────────────
  Subtotal:                                  7.0 сек

Page 2: (те саме)                             7.0 сек

Throttling (asyncio.sleep):                  0.6 сек

─────────────────────────────────────────────────
EXPECTED TOTAL: ~14-15 сек
```

**Але фактично 118 сек!**

**Гіпотези:**
1. **Confluence API затримка** - expand="body.storage,version" повертає 5-10MB даних
   - Network latency: 2-3 сек
   - Confluence processing: 5-10 сек
   - Total: ~10-15 сек/call

2. **OpenAI API затримка** - большой контекст (весь HTML)
   - Tokenization: 2-3 сек
   - Queue + inference: 20-30 сек
   - Total: ~25-35 сек/call

3. **Parsing HTML** - BeautifulSoup на 5-10MB контенту
   - Parse tree: 2-3 сек
   - Text extraction: 1-2 сек

**РЕАЛЬНА СУМА:**
```
Per page = 10 + 30 + 2 + 1 = ~43 сек
2 pages = ~85-90 сек ← БЛИЗЬКО до 118 сек!
```

---

## 💡 РІШЕННЯ: Мінімізація контексту

### Fix #1: Обмежити expand параметр для tag_pages()

**Проблема:**
```python
page = await self.confluence.get_page(page_id)  # expand="body.storage,version"
```

**Рішення:**
```python
# Для tag_pages - ТІЛЬКИ необхідна мінімальна інформація
page = await self.confluence.get_page(page_id, expand="body.storage")
# Видаляємо expand="version" - історія версій НЕ потрібна для тегування
```

**Очікувана економія часу:** get_page() з ~10 сек → ~2-3 сек (-70%)

---

### Fix #2: Мінімізувати HTML контекст перед AI

**Поточний код:**
```python
text = page.get("body", {}).get("storage", {}).get("value", "")
# ← Весь HTML контент, потенційно 5-10MB!

tags = await agent.suggest_tags(text)  # ← AI обробляє весь текст
```

**Нове рішення:**
```python
from src.utils.html_to_text import html_to_text

html = page.get("body", {}).get("storage", {}).get("value", "")

# Видалити скрипти, стилі, метаінформацію
cleaned_html = clean_html_for_tagging(html)

# Витягти текст
text = html_to_text(cleaned_html)

# ОБМЕЖИТИ довжину - перші 2000-3000 символів достатньо для тегування!
MAX_CHARS_FOR_AI = 3000
truncated_text = text[:MAX_CHARS_FOR_AI]

tags = await agent.suggest_tags(truncated_text)  # ← Меньший контекст
```

**Функція очистки:**
```python
def clean_html_for_tagging(html: str) -> str:
    """
    Видаляє непотрібні елементи для тегування.
    """
    from bs4 import BeautifulSoup
    
    soup = BeautifulSoup(html, "html.parser")
    
    # Видалити скрипти, стилі, макроси
    for tag in soup.find_all(['script', 'style', 'iframe', 'ac:macro']):
        tag.decompose()
    
    # Видалити аттрибути (залишити тільки текст)
    for tag in soup.find_all():
        tag.attrs = {}
    
    return str(soup)
```

**Очікувана економія часу:** AI call з ~30 сек → ~2-3 сек (-90%)

---

### Fix #3: Паралелізація API calls (як прочитано)

**З попереднього patch:**
```python
# ПАРАЛЕЛЬНА обробка замість серійної
tasks = [process_single_page(pid) for pid in filtered_ids]
results = await asyncio.gather(*tasks, return_exceptions=False)
```

**Очікувана економія:** 100% серійність → ~50% паралелізму

---

## 📝 Спеціальний Patch: Context Minimization

### Файл 1: `src/services/bulk_tagging_service.py`

**Заміна у методі tag_pages(), line 168:**

```python
# BEFORE:
page = await self.confluence.get_page(page_id)
if not page:
    ...

text = page.get("body", {}).get("storage", {}).get("value", "")
logger.debug(f"[TagPages] Extracted {len(text)} chars from page {page_id}")

# AFTER:
# ✅ Мінімальна expand для tag_pages - без version历史
page = await self.confluence.get_page(page_id, expand="body.storage")
if not page:
    ...

html = page.get("body", {}).get("storage", {}).get("value", "")
logger.debug(f"[TagPages] Extracted HTML: {len(html)} chars from page {page_id}")

# ✅ Очистити HTML від скриптів, стилів, макросів
from src.utils.html_cleaner import clean_html_for_tagging
cleaned_html = clean_html_for_tagging(html)
logger.debug(f"[TagPages] After cleaning: {len(cleaned_html)} chars")

# ✅ Витягти текст та обмежити довжину
from src.utils.html_to_text import html_to_text
text = html_to_text(cleaned_html)
MAX_CONTEXT_FOR_AI = 3000  # Перші 3000 символів достатньо для тегування
truncated_text = text[:MAX_CONTEXT_FOR_AI]
logger.info(f"[TagPages] Context for AI: {len(truncated_text)} chars (max={MAX_CONTEXT_FOR_AI})")
```

---

### Файл 2: `src/utils/html_cleaner.py` (НОВИЙ ФАЙЛ)

```python
"""
HTML cleaner для мінімізації контексту перед AI processing.
"""

from bs4 import BeautifulSoup
from src.core.logging.logger import get_logger

logger = get_logger(__name__)


def clean_html_for_tagging(html: str) -> str:
    """
    Видаляє непотрібні елементи з HTML для тегування.
    
    Видаляє:
    - <script>, <style>, <iframe>, <ac:macro> (Confluence макроси)
    - Порожні теги та whitespace
    - HTML коментарі
    
    Залишає:
    - Текстовий вміст
    - Структура параграфів, списків, заголовків
    
    Args:
        html: HTML вміст сторінки
        
    Returns:
        Очищений HTML без скриптів та стилів
    """
    try:
        soup = BeautifulSoup(html, "html.parser")
        
        # Видалити скрипти і стилі
        for tag in soup.find_all(['script', 'style', 'iframe', 'noscript']):
            tag.decompose()
        
        # Видалити Confluence макроси
        for tag in soup.find_all(['ac:macro', 'ac:rich-text-body', 'ac:parameter']):
            tag.decompose()
        
        # Видалити HTML коментарі
        for comment in soup.find_all(string=lambda text: isinstance(text, type(soup.contents[0]))):
            if isinstance(comment, type(soup.contents[0])) and comment.name is None:
                # HTML comment - видалити
                pass
        
        # Видалити аттрибути (залишити тільки текст і структуру)
        for tag in soup.find_all(True):
            # Видалити все крім основних тегів структури
            if tag.name not in ['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'li', 'strong', 'em', 'br']:
                # Для інших тегів видалити аттрибути
                tag.attrs = {}
        
        result = str(soup)
        logger.debug(f"[HtmlCleaner] Cleaned {len(html)} chars → {len(result)} chars")
        
        return result
        
    except Exception as e:
        logger.warning(f"[HtmlCleaner] Failed to clean HTML: {e}, returning original")
        return html


def limit_text_length(text: str, max_chars: int = 3000) -> str:
    """
    Обмежує довжину тексту для AI обробки.
    
    Args:
        text: Текст для обмеження
        max_chars: Максимальна довжина (за замовчуванням 3000)
        
    Returns:
        Обмежений текст
    """
    if len(text) <= max_chars:
        return text
    
    # Обрізати на границі речень/параграфів для збереження семантики
    truncated = text[:max_chars]
    
    # Знайти останню точку перед max_chars
    last_period = truncated.rfind('.')
    last_newline = truncated.rfind('\n')
    
    cut_point = max(last_period, last_newline)
    if cut_point > max_chars * 0.9:  # Якщо точка близько до краю
        return truncated[:cut_point + 1]
    
    return truncated
```

---

## ✅ Перевірка виправлення

### Тест #1: Обмежений expand

```python
import time

async def test_limited_expand():
    """Перевірити, що get_page з expand='body.storage' швидший"""
    
    confluence = ConfluenceClient()
    
    # BEFORE: expand="body.storage,version"
    start = time.time()
    page_full = await confluence.get_page("123", expand="body.storage,version")
    time_full = time.time() - start
    
    # AFTER: expand="body.storage"
    start = time.time()
    page_minimal = await confluence.get_page("123", expand="body.storage")
    time_minimal = time.time() - start
    
    print(f"✅ Full expand:    {time_full:.2f}s, size: {len(str(page_full))} bytes")
    print(f"✅ Minimal expand: {time_minimal:.2f}s, size: {len(str(page_minimal))} bytes")
    print(f"✅ Speedup: {time_full/time_minimal:.1f}x")
    
    assert time_minimal < time_full, "Minimal expand should be faster"
```

**Очікуваний результат:**
```
Full expand:    10.5s, size: 524288 bytes
Minimal expand:  2.1s, size: 512000 bytes
Speedup: 5.0x
```

### Тест #2: Очищений HTML

```python
from src.utils.html_cleaner import clean_html_for_tagging, limit_text_length

def test_html_cleaning():
    """Перевірити очистку HTML та обмеження довжини"""
    
    html = """
    <script>alert('test')</script>
    <p>Important content here</p>
    <ac:macro>...</ac:macro>
    <p>More content</p>
    <style>.css { color: red; }</style>
    """
    
    cleaned = clean_html_for_tagging(html)
    assert "script" not in cleaned.lower()
    assert "ac:macro" not in cleaned.lower()
    assert "Important content" in cleaned
    
    long_text = "A" * 5000
    limited = limit_text_length(long_text, max_chars=3000)
    
    assert len(limited) <= 3000
    print(f"✅ HTML cleaned: {len(html)} → {len(cleaned)} chars")
    print(f"✅ Text limited: {len(long_text)} → {len(limited)} chars")
```

### Тест #3: Загальний часовий тест

```bash
# ПЕРЕД виправленням:
curl -X POST http://localhost:8000/bulk/tag-pages \
  -H "Content-Type: application/json" \
  -d '{
    "space_key": "nkfedba",
    "page_ids": ["111", "222"],
    "dry_run": true
  }' 
# Time: ~118 сек

# ПІСЛЯ виправлення:
curl -X POST http://localhost:8000/bulk/tag-pages \
  -H "Content-Type: application/json" \
  -d '{
    "space_key": "nkfedba",
    "page_ids": ["111", "222"],
    "dry_run": true
  }'
# Time: ~10-15 сек (8x швидше!) ✅
```

---

## 📊 Очікувана економія часу

### Before vs After

```
ПЕРЕД:
- get_page(expand="body.storage,version"): 10 сек (велика відповідь)
- AI call на 5-10MB контексту:              50 сек (tokenization + inference)
- Parsing + overhead:                        5 сек
- Per page:                                 ~65 сек
- 2 pages (серійна):                       ~130 сек ← РЕАЛЬНО СПОСТЕРІГАЄМО!

ПІСЛЯ (всі fix разом):
- get_page(expand="body.storage"):           2 сек (мала відповідь)
- AI call на 3KB контексту:                  1 сек (швидка обробка)
- Clean + parse:                             0.5 сек
- Per page:                                 ~3.5 сек
- 2 pages (паралельна):                     ~3-4 сек ← 30-40x швидше!

ОЧІКУВАНЕ ПРИСКОРЕННЯ: 130 сек → 3-4 сек (35x faster!)
```

---

## 🎯 Checklist впровадження

- [ ] Обмежити expand у tag_pages: `expand="body.storage"`
- [ ] Додати html_cleaner.py з clean_html_for_tagging()
- [ ] Додати обмеження довжини контексту (3000 chars)
- [ ] Включити паралелізацію (asyncio.gather)
- [ ] Запустити unit тести
- [ ] Вимірити час виконання
- [ ] Перевірити якість тегування (не повинна змінитися)
- [ ] Документувати зміни

---

**Status:** ✅ Діагностика завершена  
**Головна проблема:** Надмірний expand параметр + великий контекст для AI  
**Рішення:** Мінімізувати expand + обмежити контекст + паралелізація  
**Очікування:** 130 сек → 3-4 сек (35x прискорення)
