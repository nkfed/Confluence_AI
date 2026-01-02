# Tag-Space: Whitelist завжди активний (всі режими)

## 🎯 Зміни

**Whitelist тепер застосовується в усіх режимах для `/bulk/tag-space/{space_key}`:**
- TEST
- SAFE_TEST  
- PROD

## 📋 Режимна матриця для tag-space

| Режим | Scope | dry_run=true | dry_run=false/None | Записи в Confluence |
|-------|-------|--------------|-------------------|-------------------|
| **TEST** | whitelist | Симуляція (примусово) | Симуляція (примусово) | ❌ Ніколи |
| **SAFE_TEST** | whitelist | Симуляція | Реальний запис | ✅ Якщо dry_run=false |
| **PROD** | whitelist | Симуляція | Реальний запис | ✅ Якщо dry_run=false |

### Пояснення:

**Scope (які сторінки обробляються):**
- Завжди контролюється через `whitelist_config.json`
- Обробляються тільки entry points + їх піддерева
- Сторінки поза whitelist пропускаються

**dry_run (чи записувати зміни):**
- `true` → тільки симуляція, статус="dry_run", update_labels не викликається
- `false/None` → реальний запис (якщо режим дозволяє)

## 🔄 Що змінилось

### До виправлення:

```python
# ❌ СТАРИЙ КОД
whitelist_enabled = mode in ["TEST", "SAFE_TEST"]

if whitelist_enabled:
    allowed_ids = await whitelist_manager.get_allowed_ids(...)
else:
    # PROD: обробляються ВСІ сторінки простору
    allowed_ids = None
```

### Після виправлення:

```python
# ✅ НОВИЙ КОД
whitelist_enabled = True  # Завжди для tag-space

# Завжди завантажуємо whitelist
allowed_ids = await whitelist_manager.get_allowed_ids(space_key, confluence_client)

# Завжди фільтруємо за whitelist
for page_id in all_pages:
    if whitelist_manager.is_allowed(space_key, page_id, allowed_ids):
        pages_to_process.append(page_id)
```

## 📊 Приклади

### PROD + dry_run=true

**До:**
```json
// PROD без whitelist - обробляє ВСІ 100 сторінок простору
{
  "mode": "PROD",
  "whitelist_enabled": false,
  "total": 100,
  "processed": 100,
  "skipped_by_whitelist": 0
}
```

**Після:**
```json
// PROD з whitelist - обробляє тільки 10 whitelist сторінок
{
  "mode": "PROD",
  "whitelist_enabled": true,
  "dry_run": true,
  "total": 100,
  "processed": 10,
  "skipped_by_whitelist": 90,
  "details": [
    {"page_id": "100", "status": "dry_run"},
    {"page_id": "101", "status": "dry_run"}
  ]
}
```

### PROD + dry_run=false

**Після:**
```json
// PROD з whitelist - записує тільки whitelist сторінки
{
  "mode": "PROD",
  "whitelist_enabled": true,
  "dry_run": false,
  "total": 100,
  "processed": 10,
  "skipped_by_whitelist": 90,
  "details": [
    {"page_id": "100", "status": "updated"},
    {"page_id": "101", "status": "updated"}
  ]
}
```

## 📝 Логування

**Нове логування:**

```
[TagSpace] Using whitelist for scope in mode=PROD, dry_run=false. 
           Whitelist controls which pages are processed, dry_run controls whether to write.
[TagSpace] Whitelist loaded: 10 allowed pages for MYSPACE
[TagSpace] Allowed IDs (first 20): [100, 101, 102, 103, ...]
[TagSpace] Found 100 total pages in space 'MYSPACE'
[TagSpace] After whitelist filter: 10 to process, 90 skipped. Mode=PROD, dry_run=false
```

## ✅ Що НЕ змінилось

**Гарантії збереження функціональності:**

1. **SAFE_TEST + dry_run=false** - реальний запис працює ✅
2. **TEST режим** - примусовий dry_run ✅
3. **Інші ендпоінти** (tag-tree, tag-pages, auto-tag) - не змінені ✅
4. **Whitelist піддерева** - рекурсивний обхід працює ✅
5. **Логіка дозволів** - allowed_ids передається в tag_pages() ✅

## 🧪 Тести

**Додано нові тести:**

1. `test_prod_mode_uses_whitelist_dry_run_true`
   - PROD + dry_run=true
   - Обробляються тільки whitelist
   - update_labels НЕ викликається

2. `test_prod_mode_uses_whitelist_dry_run_false`
   - PROD + dry_run=false
   - Обробляються тільки whitelist
   - Реальний запис дозволений

3. `test_safe_test_dry_run_does_not_write`
   - SAFE_TEST + dry_run=true
   - update_labels НЕ викликається
   - Перевірка що dry_run блокує запис

**Результати:**
```
✅ 26/26 базових тестів проходять
✅ Нові тести для PROD режиму проходять
✅ Не зламано існуючу функціональність
```

## 🚀 Використання

### Конфігурація whitelist

**`whitelist_config.json`:**
```json
{
  "spaces": [
    {
      "space_key": "MYSPACE",
      "pages": [
        {"id": 100, "name": "Root", "root": true}
      ]
    }
  ]
}
```

### Запити

**TEST режим (завжди dry-run):**
```bash
curl -X POST "http://localhost:8000/bulk/tag-space/MYSPACE"
# → Обробляє whitelist, симуляція
```

**SAFE_TEST dry-run:**
```bash
curl -X POST "http://localhost:8000/bulk/tag-space/MYSPACE?dry_run=true"
# → Обробляє whitelist, симуляція
```

**SAFE_TEST запис:**
```bash
curl -X POST "http://localhost:8000/bulk/tag-space/MYSPACE?dry_run=false"
# → Обробляє whitelist, реальний запис
```

**PROD dry-run:**
```bash
curl -X POST "http://localhost:8000/bulk/tag-space/MYSPACE?dry_run=true"
# → Обробляє whitelist, симуляція
```

**PROD запис:**
```bash
curl -X POST "http://localhost:8000/bulk/tag-space/MYSPACE?dry_run=false"
# → Обробляє whitelist, реальний запис
```

## ⚠️ Важливо

**Whitelist обов'язковий для tag-space:**

Якщо в `whitelist_config.json` немає entry points для space_key:

```json
{
  "total": 0,
  "processed": 0,
  "errors": 0,
  "details": [{
    "status": "error",
    "message": "No whitelist entries for space MYSPACE. Add entries to whitelist_config.json"
  }]
}
```

**Рішення:** Додати space до `whitelist_config.json`.

## 📚 Файли

**Змінено:**
- `src/services/bulk_tagging_service.py` - whitelist завжди активний

**Тести:**
- `tests/test_tag_space_whitelist_integration.py` - додано тести для PROD

**Документація:**
- `docs/TAG_SPACE_WHITELIST_ALWAYS_ON.md` - цей документ

## 🎯 Переваги

1. **Консистентність** - whitelist працює однаково в усіх режимах
2. **Безпека** - PROD не може "випадково" обробити весь простір
3. **Контроль** - scope завжди керується через whitelist_config.json
4. **Прозорість** - режимна матриця зрозуміла і передбачувана
5. **Гнучкість** - dry_run керує записом, незалежно від scope
