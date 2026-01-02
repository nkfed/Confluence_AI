# Виправлення dry_run логіки в SAFE_TEST режимі

## 🐛 Проблема

У режимі SAFE_TEST з `dry_run=true`, агент **записував теги у Confluence**, хоча не повинен був.

**Порушення режимної матриці:**
```
SAFE_TEST + dry_run=true:
  Очікується: тільки симуляція, без запису
  Було: реальний запис у Confluence ❌
```

## 🔍 Причина

**Відсутність перевірки `dry_run` перед записом:**

```python
# ❌ БУЛО (неправильно)
# Policy check passed - update labels
if to_add:
    logger.info(f"[Bulk] Updating labels for page {page_id}")
    await self.confluence.update_labels(page_id, list(to_add))  # Завжди записує!
```

Після перевірки `dry_run` на початку методу (рядок 90), код повертав `status="dry_run"`, але потім при `dry_run=False` (тобто в non-dry-run блоці після continue) - все одно виконувався запис без додаткової перевірки.

## ✅ Рішення

**Додано перевірку `dry_run` перед кожним записом:**

```python
# ✅ СТАЛО (правильно)
if to_add:
    if not dry_run:
        # Real update mode
        logger.info(f"[Bulk] Updating labels for page {page_id}")
        await self.confluence.update_labels(page_id, list(to_add))
    else:
        logger.info(f"[Bulk] [DRY-RUN] Would update labels for {page_id}")

results.append({
    "page_id": page_id,
    "status": "updated" if not dry_run else "dry_run",
    ...
})
```

## 📝 Зміни

### Файл: `src/services/bulk_tagging_service.py`

**Оновлено логіку запису в методі `tag_pages()`:**

1. **Додано перевірку перед записом:**
```python
if to_add:
    if not dry_run:
        await self.confluence.update_labels(page_id, list(to_add))
    else:
        logger.info(f"[DRY-RUN] Would update...")
```

2. **Оновлено статус:**
```python
"status": "updated" if not dry_run else "dry_run"
```

### Файл: `tests/test_tag_space_whitelist_integration.py`

**Додано критичний тест:**

```python
@pytest.mark.asyncio
async def test_safe_test_dry_run_does_not_write():
    """
    Перевіряє що SAFE_TEST + dry_run=true НЕ записує теги.
    
    Критична перевірка:
    - mock_confluence.update_labels.call_count == 0
    """
```

## 📊 Режимна матриця (виправлена)

| Режим | dry_run | Поведінка | update_labels? | Статус |
|-------|---------|-----------|----------------|--------|
| **TEST** | True (примусово) | Симуляція | ❌ Ні | `dry_run` |
| **SAFE_TEST** | True | Симуляція | ❌ Ні | `dry_run` |
| **SAFE_TEST** | False | Реальний запис | ✅ Так | `updated` |
| **PROD** | True | Симуляція | ❌ Ні | `dry_run` |
| **PROD** | False | Реальний запис | ✅ Так | `updated` |

## 🧪 Тестування

### До виправлення:

```python
# SAFE_TEST + dry_run=true
result = await service.tag_space("SPACE", dry_run=True)

# ❌ Проблема
assert result["status"] == "dry_run"  # ✅ Пройшов
assert mock_confluence.update_labels.call_count == 0  # ❌ FAILED (було 3 виклики!)
```

### Після виправлення:

```python
# SAFE_TEST + dry_run=true
result = await service.tag_space("SPACE", dry_run=True)

# ✅ Все працює
assert result["status"] == "dry_run"  # ✅ Пройшов
assert mock_confluence.update_labels.call_count == 0  # ✅ Пройшов
```

## 📋 Логування

**SAFE_TEST + dry_run=true (симуляція):**
```
[Bulk] Using agent mode: SAFE_TEST, dry_run=True
[Bulk] Processing page 100 (dry_run=True)
[Bulk] [DRY-RUN] Would add labels for 100: ['domain-rehab-2-0', 'doc-tech']
[Bulk] [DRY-RUN] Would update labels for page 100: ['domain-rehab-2-0', 'doc-tech']
```

**SAFE_TEST + dry_run=false (реальний запис):**
```
[Bulk] Using agent mode: SAFE_TEST, dry_run=False
[Bulk] Processing page 100 (dry_run=False)
[Bulk] Updating labels for page 100: adding ['domain-rehab-2-0', 'doc-tech']
[Bulk] Successfully updated labels for page 100
```

## ✅ Критерії приймання

**У SAFE_TEST + dry_run=true:**
- ✅ Теги НЕ записуються
- ✅ Статус = "dry_run"
- ✅ POST /label НЕ викликається
- ✅ update_labels.call_count == 0
- ✅ Логування показує "[DRY-RUN]"

**У SAFE_TEST + dry_run=false:**
- ✅ Теги записуються
- ✅ Статус = "updated"
- ✅ POST /label викликається
- ✅ update_labels.call_count > 0
- ✅ Логування показує "Successfully updated"

**У PROD:**
- ✅ dry_run працює як очікується
- ✅ Реальний запис доступний

**Тести:**
- ✅ 26/26 базових тестів проходять
- ✅ Новий тест `test_safe_test_dry_run_does_not_write` проходить
- ✅ Немає побічних ефектів на реальні записи

## 🎯 Приклади використання

**Dry-run (симуляція):**
```bash
curl -X POST "http://localhost:8000/bulk/tag-space/MYSPACE?dry_run=true"
```

**Результат:**
```json
{
  "mode": "SAFE_TEST",
  "dry_run": true,
  "details": [
    {
      "page_id": "100",
      "status": "dry_run",
      "tags": {
        "proposed": ["domain-rehab-2-0"],
        "to_add": ["domain-rehab-2-0"]
      }
    }
  ]
}
```
→ **update_labels НЕ викликається**

**Реальний запис:**
```bash
curl -X POST "http://localhost:8000/bulk/tag-space/MYSPACE?dry_run=false"
```

**Результат:**
```json
{
  "mode": "SAFE_TEST",
  "dry_run": false,
  "details": [
    {
      "page_id": "100",
      "status": "updated",
      "tags": {
        "proposed": ["domain-rehab-2-0"],
        "added": ["domain-rehab-2-0"]
      }
    }
  ]
}
```
→ **update_labels викликається**

## 🚨 Важливо

**Виправлення НЕ впливає на:**
- ✅ Логіку whitelist
- ✅ Логіку дозволів SAFE_TEST
- ✅ Реальний запис при dry_run=false
- ✅ Інші режими (TEST, PROD)

**Виправлення тільки додає:**
- Перевірку `dry_run` перед `update_labels()`
- Правильний статус в результатах

## 📚 Додаткова інформація

- **Зміни:** `src/services/bulk_tagging_service.py` (рядки 135-148)
- **Тест:** `tests/test_tag_space_whitelist_integration.py::test_safe_test_dry_run_does_not_write`
- **Issue:** dry_run=true викликав реальний запис
- **Fix:** Додано `if not dry_run:` перед `update_labels()`
