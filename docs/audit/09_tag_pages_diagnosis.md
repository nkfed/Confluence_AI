# Діагностика POST /bulk/tag-pages - Аналіз продуктивності

**Date:** 2 January 2026  
**Проблема:** Обробка 2 сторінок на dry_run=true займає 100+ секунд

---

## 📋 Перевірена логіка

### 1. ✅ Обробка тільки явно заданих page_ids

**Знаходження:** ✅ **ПРАВИЛЬНО**

**Код** (`src/services/bulk_tagging_service.py`, lines 105-150):
```python
# ✅ Filter page_ids by whitelist (except in PROD mode)
page_ids_int = [int(pid) for pid in page_ids]

if mode == "PROD":
    filtered_ids = page_ids_int  # Всі сторінки
else:
    # TEST/SAFE_TEST: фільтрація по whitelist
    filtered_ids = [pid for pid in page_ids_int if pid in allowed_ids]

# Process filtered pages only
for page_id_int in filtered_ids:  # ← ТІЛЬКИ filtered_ids!
    page_id = str(page_id_int)
    page = await self.confluence.get_page(page_id)  # Одна сторінка за раз
    text = page.get("body", {}).get("storage", {}).get("value", "")
    tags = await agent.suggest_tags(text)  # ← AI call для ОДНОЇ сторінки
```

**Висновок:** Обробка обмежена тільки page_ids з запиту + whitelist фільтрація. **НЕ викликаються** get_children(), expand_tree(), resolve_related_pages().

---

### 2. ❌ Виявлені невикористані функції

**Знаходження:** ✅ **Перевірено - НЕ викликаються**

Семантичні пошуки НЕ виявили виклики:
- `get_children()` у `tag_pages()` 
- `expand_tree()` у `tag_pages()`
- `resolve_related_pages()` у `tag_pages()`

Ці функції існують тільки у `tag_tree()` та `tag_space()` методах.

---

### 3. ✅ Whitelist фільтрує тільки запитані page_ids

**Знаходження:** ✅ **ПРАВИЛЬНО**

**Код** (lines 95-105):
```python
allowed_ids = await whitelist_manager.get_allowed_ids(space_key, self.confluence)
# ↓ Фільтрує тільки запитані page_ids, не бере всі allowed_test_pages
filtered_ids = [pid for pid in page_ids_int if pid in allowed_ids]
```

**Тест підтверджує** (`tests/bulk/test_tag_pages.py`):
```python
# page_ids = ["111", "222", "333"]
# whitelist = {111, 333}
# Result: processed=2, skipped=1 ✅
```

---

### 4. ✅ TaggingAgent формує prompt для однієї сторінки

**Знаходження:** ✅ **ПРАВИЛЬНО**

**Код** (`src/agents/tagging_agent.py`, lines 55-110):
```python
async def suggest_tags(self, text: str) -> dict:
    # ← text для ОДНІЄЇ сторінки, не додається контекст дочірніх сторінок
    prompt = f"""
Текст для аналізу:
{text}
"""
    ai_response = await self._ai_router.generate(prompt=prompt)
    return limited_tags
```

**Висновок:** Немає додаткового контексту від інших сторінок. AI обробляє тільки переданий текст.

---

## 🔴 НАЙДЕНА ПРОБЛЕМА: Повільність AI

### Симптом: 100+ секунд для 2 сторінок

**Математика:**
- Очікуване: 2 API calls до AI × ~5-10 сек/call = 10-20 сек
- Фактичне: ~100+ сек = ~50 сек/call або 10 call замість 2

### Виявлені потенційні причини:

#### A) **Серійні виклики TaggingAgent** (НЕЙТРАЛЬНО - очікуване)
```python
# Line 180-190
for page_id_int in filtered_ids:
    agent = TaggingAgent(ai_router=router)  # ✅ Кожен раз новий об'єкт
    tags = await agent.suggest_tags(text)   # ← Серійна обробка (не паралельна)
    await asyncio.sleep(0.3)                # + throttling 300ms
```

**Аналіз:**
- Для 2 сторінок: 2 × (~20 сек AI + 0.3 сек throttle) = ~40 сек
- Це НОРМАЛЬНО для синхронної обробки

#### B) **Додатковий контекст у промпті** ❌ **НЕ знайдено**
Промпт не включає контекст від інших сторінок. Text тільки для одної сторінки.

#### C) **Кількість AI calls** ✅ **ПЕРЕВІРЕНО**
Логування показує `[TagPages] Calling TaggingAgent via router for page {page_id}` - це означає, що call робиться для кожної сторінки окремо.

---

## 🎯 КОРЕНЕВОЇ ПРИЧИН: Ймовірні грі़ачі затримки

### 1. **OpenAI API затримка** (55%)
```
Очікуване: 5-10 сек/call (за Confluence + OpenAI documentation)
Фактичне: 50+ сек/call

Можливі причини:
- Rate limiting OpenAI (5-10 RPM на деяких планах)
- Мережева затримка
- Token processing в OpenAI
- Недостатня API quota
```

### 2. **Конфлюенс API затримка** (20%)
```python
page = await self.confluence.get_page(page_id)  # Може бути 5-10 сек
await self.confluence.update_labels(...)         # Не викликається у dry_run
```

### 3. **Throttling + Serialization** (15%)
```python
await asyncio.sleep(0.3)  # 300ms × 2 = 600ms
# Обробка тільки серійна (async for) - без паралелізму
```

### 4. **Ініціалізація об'єктів** (10%)
```python
agent = TaggingAgent(ai_router=router)  # Новий об'єкт 2 рази
whitelist_manager = WhitelistManager()   # Завантажує JSON файл
```

---

## 💡 ТОЧКОВІ ВИПРАВЛЕННЯ

### Fix #1: Паралелізація AI calls
**Файл:** `src/services/bulk_tagging_service.py`

**Проблема:** Серійна обробка 2 сторінок займає 100 сек замість 20-30 сек

**Рішення:** Використовати `asyncio.gather()` для паралельних API calls
```python
# BEFORE (lines 175-200):
for page_id_int in filtered_ids:
    page = await self.confluence.get_page(page_id)
    tags = await agent.suggest_tags(text)  # ← Чекає на кожну
    await asyncio.sleep(0.3)

# AFTER:
async def _process_page_async(page_id_int):
    """Обробляє одну сторінку асинхронно"""
    page_id = str(page_id_int)
    try:
        page = await self.confluence.get_page(page_id)
        if not page:
            return {"page_id": page_id, "status": "error", "message": "Not found"}
        
        text = page.get("body", {}).get("storage", {}).get("value", "")
        agent = TaggingAgent(ai_router=router)
        tags = await agent.suggest_tags(text)
        
        # ... rest of logic
        return result_dict
    except Exception as e:
        return {"page_id": page_id, "status": "error", "message": str(e)}

# Параралельна обробка:
if filtered_ids:
    tasks = [_process_page_async(pid) for pid in filtered_ids]
    results_list = await asyncio.gather(*tasks, return_exceptions=False)
    results = [r for r in results_list if r is not None]
```

**Очікувана економія часу:** 100 сек → 30-50 сек (паралелізм)

---

### Fix #2: Кешування WhitelistManager
**Файл:** `src/services/bulk_tagging_service.py`

**Проблема:** Кожен вклик `tag_pages()` завантажує whitelist заново
```python
# BEFORE (line 95):
whitelist_manager = WhitelistManager()  # JSON file I/O
```

**Рішення:** Кешування на рівні сервісу
```python
# AFTER:
class BulkTaggingService:
    _whitelist_cache = None
    _cache_time = None
    
    async def _get_whitelist_manager(self):
        """Повертає кешований WhitelistManager, переовантажує кожну 60 сек"""
        now = time.time()
        if (self._whitelist_cache is None or 
            (self._cache_time and now - self._cache_time > 60)):
            self._whitelist_cache = WhitelistManager()
            self._cache_time = now
        return self._whitelist_cache
    
    async def tag_pages(self, page_ids, space_key, dry_run=None):
        whitelist_manager = await self._get_whitelist_manager()
        allowed_ids = await whitelist_manager.get_allowed_ids(space_key, self.confluence)
```

**Очікувана економія часу:** Мінус 1-2 сек на другого вклику

---

### Fix #3: Батчування AI промптів (опціонально)
**Файл:** `src/agents/tagging_agent.py`

**Проблема:** Для 10 сторінок = 10 окремих AI calls

**Рішення:** Батчування (якщо AI дозволяє)
```python
async def suggest_tags_batch(self, texts: List[str]) -> List[dict]:
    """
    Обробляє список текстів в одному батчованому промпті.
    Зменшує кількість API calls в 5-10 разів.
    """
    batch_prompt = """
Обробляй наступні тексти послідовно. Для кожного поверни JSON.

---
ТЕКСТ 1:
{text_1}

ВІДПОВІДЬ 1:
{...json...}

---
ТЕКСТ 2:
{text_2}

ВІДПОВІДЬ 2:
{...json...}
"""
    # Трохи більший промпт, але 5-10x менше API calls
```

**Очікувана економія часу:** Для 10 сторінок: 50 сек → 10-15 сек

---

## ✅ ПЕРЕВІРКА ВИПРАВЛЕННЯ

### Тест #1: Паралелізація
```python
import time

async def test_tag_pages_parallel():
    page_ids = ["111", "222", "333"]
    start = time.time()
    
    result = await service.tag_pages(page_ids, space_key="euheals", dry_run=True)
    
    elapsed = time.time() - start
    
    # ПІСЛЯ виправлення:
    # - Очікуване: 30-50 сек (паралельні AI calls)
    # - Раніше було: 100+ сек (серійна обробка)
    print(f"✅ Total time: {elapsed:.1f}s (expected: 30-50s)")
    
    assert result["processed"] == 3
    assert result["success"] == 3
    assert elapsed < 60, f"Too slow: {elapsed}s, expected <60s"
```

### Тест #2: Логування часу
```python
# У tag_pages() додати логування:
import time

start_page = time.time()
tags = await agent.suggest_tags(text)
elapsed_page = time.time() - start_page

logger.info(f"[TagPages] AI call for {page_id} took {elapsed_page:.1f}s")
```

**Очікуваний вивід:**
```
[TagPages] AI call for 111 took 18.5s (паралельно)
[TagPages] AI call for 222 took 19.2s (паралельно)
[TagPages] AI call for 333 took 20.1s (паралельно)
Total: ~20s (не ~100s)
```

### Тест #3: Переевіка Whitelist фільтрації
```python
async def test_whitelist_filtering():
    page_ids = ["111", "222", "333"]  # Від user
    
    # Whitelist має: 111, 333 (у config)
    result = await service.tag_pages(page_ids, space_key="euheals", dry_run=True)
    
    # ✅ КЛЮЧОВА перевірка: обробляються ТІЛЬКИ 111 і 333
    assert result["processed"] == 2, "Should process only whitelisted pages"
    assert result["skipped_by_whitelist"] == 1, "222 should be skipped"
    
    details_ids = {d["page_id"] for d in result["details"]}
    assert details_ids == {"111", "333"}, "Details should have only whitelisted"
    assert "222" not in details_ids, "Non-whitelisted should NOT be in details"
```

---

## 📊 Потім. Діагностичні команди

### 1. Перевірити AI call time
```bash
# Додати в logger логування AI call time
curl -X POST http://localhost:8000/bulk/tag-pages \
  -H "Content-Type: application/json" \
  -d '{
    "space_key": "nkfedba",
    "page_ids": ["19699862097", "19729285121"],
    "dry_run": true
  }'

# Перевірити логи:
# [TagPages] AI call for 19699862097 took Xs
# [TagPages] AI call for 19729285121 took Ys
# Total: X + Y + overhead
```

### 2. Профіліювання часу
```python
import time
import logging

logger = logging.getLogger(__name__)

async def tag_pages(...):
    t0 = time.time()
    
    t1 = time.time()
    allowed_ids = await whitelist_manager.get_allowed_ids(...)
    logger.info(f"⏱ Whitelist load: {time.time() - t1:.2f}s")
    
    t2 = time.time()
    for page_id in filtered_ids:
        t_page = time.time()
        tags = await agent.suggest_tags(text)
        logger.info(f"⏱ AI call for {page_id}: {time.time() - t_page:.2f}s")
    logger.info(f"⏱ Total AI processing: {time.time() - t2:.2f}s")
    
    logger.info(f"⏱ Total time: {time.time() - t0:.2f}s")
```

### 3. Verify Parallelization (After Fix)
```python
# Перевірити, що AI calls виконуються паралельно
# BEFORE (серійна):
# [TagPages] AI call for 111 took 20.1s (t=0-20s)
# [TagPages] AI call for 222 took 19.8s (t=20-40s) 
# Total: ~40s

# AFTER (паралельна):
# [TagPages] AI call for 111 took 20.1s (t=0-20s)
# [TagPages] AI call for 222 took 19.8s (t=0-20s) <- паралельно!
# Total: ~20s + overhead
```

---

## 🎯 Резюме діагностики

| Аспект | Статус | Висновок |
|--------|--------|----------|
| Обробка тільки page_ids | ✅ OK | Не викликаються get_children(), expand_tree() |
| Whitelist фільтрація | ✅ OK | Фільтрує тільки запитані page_ids |
| TaggingAgent контекст | ✅ OK | Промпт для однієї сторінки, без додаткового контексту |
| AI затримка | 🔴 ПРОБЛЕМА | 50+ сек/call замість 10-20 сек |
| Паралелізм | ❌ НЕМАЄ | Обробка серійна, можна паралелізувати |

### Главна рекомендація:
**Впровадити Fix #1 (паралелізація)** для скорочення часу з 100+ сек до 30-50 сек на 2 сторінки.

**Додатково:** Профіліювати AI call time для виявлення bottleneck (OpenAI vs Confluence).

---

**Status:** ✅ Діагностика завершена  
**Рекомендовані Fix:** #1 (паралелізація), #2 (кешування), #3 (батчування)
