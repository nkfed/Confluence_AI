# Видалення залежності від TAGGING_AGENT_TEST_PAGE

## 🎯 Проблема

У режимі SAFE_TEST, `TaggingAgent` блокував сторінки які:
- ✅ Входять у `whitelist_config.json`
- ❌ Не входять у `TAGGING_AGENT_TEST_PAGE` (.env)

Це суперечило новій логіці централізованого whitelist керування.

## 🔍 Причина

**Подвійна перевірка whitelist:**

1. **WhitelistManager** → фільтрує сторінки за `whitelist_config.json`
2. **BaseAgent.enforce_page_policy()** → перевіряє `.env` (`TAGGING_AGENT_TEST_PAGE`)

**Результат:** Навіть якщо сторінка в whitelist піддереві, вона блокувалась через `.env`.

## ✅ Рішення

Додано параметр `allowed_ids` в `tag_pages()` який перевизначає `.env` whitelist.

### Зміни

**1. Файл: `src/services/bulk_tagging_service.py`**

**Оновлено сигнатуру `tag_pages()`:**
```python
async def tag_pages(
    self, 
    page_ids: list[str], 
    dry_run: bool = None, 
    allowed_ids: set = None  # ← Новий параметр
) -> dict:
```

**Додано логіку перевірки:**
```python
# Use allowed_ids if provided, otherwise use .env whitelist
if allowed_ids is not None:
    # Custom whitelist (from WhitelistManager)
    page_id_int = int(page_id)
    if self.agent.mode in ["TEST", "SAFE_TEST"] and page_id_int not in allowed_ids:
        raise PermissionError(...)
else:
    # Legacy .env whitelist check
    self.agent.enforce_page_policy(page_id)
```

**Оновлено `tag_space()`:**
```python
result = await self.tag_pages(
    pages_to_process, 
    dry_run=dry_run,
    allowed_ids=allowed_ids if whitelist_enabled else None
)
```

**2. Файл: `tests/test_tag_space_whitelist_integration.py`**

**Додано новий тест:**
```python
@pytest.mark.asyncio
async def test_safe_test_allows_whitelist_subtree():
    """
    Перевіряє що SAFE_TEST дозволяє:
    - Entry points з whitelist
    - Всі дочірні сторінки
    - Не використовує TAGGING_AGENT_TEST_PAGE
    """
```

## 📊 Поведінка до/після

### До виправлення:

**Конфігурація:**
```json
whitelist_config.json: {pages: [100]}  // 100 → 101 → 102
.env: TAGGING_AGENT_TEST_PAGE=100
```

**Результат у SAFE_TEST:**
```
100: ✅ updated (в whitelist_config.json і в .env)
101: ❌ forbidden (в whitelist піддереві, але НЕ в .env)
102: ❌ forbidden (в whitelist піддереві, але НЕ в .env)
```

### Після виправлення:

**Конфігурація:**
```json
whitelist_config.json: {pages: [100]}  // 100 → 101 → 102
.env: TAGGING_AGENT_TEST_PAGE=100  (ігнорується для tag-space)
```

**Результат у SAFE_TEST:**
```
100: ✅ updated (entry point)
101: ✅ updated (дочірня, успадкована з whitelist)
102: ✅ updated (дочірня, успадкована з whitelist)
```

## 🔧 Режимна логіка

### TEST режим:
```
- allowed_ids: з WhitelistManager
- dry_run: завжди True
- .env whitelist: ігнорується
```

### SAFE_TEST режим:
```
- allowed_ids: з WhitelistManager
- dry_run: False (реальний запис)
- .env whitelist: ігнорується
```

### PROD режим:
```
- allowed_ids: None (всі дозволені)
- dry_run: False
- .env whitelist: ігнорується
```

## ✅ Критерії приймання

**У SAFE_TEST режимі:**
- ✅ Обробляються всі whitelist entry points
- ✅ Обробляються всі дочірні сторінки
- ✅ Не перевіряється TAGGING_AGENT_TEST_PAGE
- ✅ Реальний запис (dry_run=False працює)

**У TEST режимі:**
- ✅ Обробляються whitelist entry points + дочірні
- ✅ Dry-run режим (без запису)

**У PROD режимі:**
- ✅ Whitelist ігнорується
- ✅ Обробляються всі сторінки
- ✅ Реальний запис

**Тести:**
- ✅ 26/26 базових тестів проходять
- ✅ Додано тест `test_safe_test_allows_whitelist_subtree`
- ✅ Логування показує дозволені сторінки

## 📋 Логування

**SAFE_TEST з whitelist:**
```
[Bulk] Using agent mode: SAFE_TEST, dry_run=False
[Bulk] Starting tagging for 3 pages (mode=SAFE_TEST, dry_run=False, allowed_ids=custom)
[Bulk] Page 100 allowed by custom whitelist
[Bulk] Page 101 allowed by custom whitelist
[Bulk] Page 102 allowed by custom whitelist
```

**PROD без whitelist:**
```
[Bulk] Using agent mode: PROD, dry_run=False
[Bulk] Starting tagging for 100 pages (mode=PROD, dry_run=False, allowed_ids=from .env)
```

## 🚀 Використання

**Для розробників:**
```python
# tag_space автоматично використовує WhitelistManager
service = BulkTaggingService()
result = await service.tag_space("MYSPACE", dry_run=False)
```

**Для ручних викликів tag_pages:**
```python
# Можна явно передати allowed_ids
allowed_ids = {100, 101, 102}
result = await service.tag_pages(page_ids, allowed_ids=allowed_ids)
```

## 📚 Backwards Compatibility

**Старий код залишається працюючим:**
```python
# Виклик без allowed_ids → використовує .env whitelist
result = await service.tag_pages(page_ids, dry_run=True)
```

**Новий код використовує WhitelistManager:**
```python
# tag_space передає allowed_ids автоматично
result = await service.tag_space(space_key, dry_run=False)
```

## 🔍 Додаткова інформація

- **Зміни:** `src/services/bulk_tagging_service.py`
- **Тести:** `tests/test_tag_space_whitelist_integration.py`
- **Залежить від:** WhitelistManager
- **.env:** `TAGGING_AGENT_TEST_PAGE` більше не використовується для `tag_space`
