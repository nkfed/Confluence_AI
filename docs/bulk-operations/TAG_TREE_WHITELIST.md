# Tag-Tree: Інтеграція з WhitelistManager

## 🎯 Зміни

**Tag-tree тепер використовує централізований whitelist з `whitelist_config.json`:**
- Root page перевіряється через whitelist
- Обробляються тільки whitelist сторінки + їх піддерева
- Старі `.env` списки більше не використовуються
- Режимна матриця збережена

## 📋 Нова сигнатура ендпоінту

**Було:**
```
POST /bulk/tag-tree/{root_page_id}
```

**Стало:**
```
POST /bulk/tag-tree/{space_key}/{root_page_id}
```

**Параметри:**
- `space_key` - ключ простору для whitelist lookup (обов'язковий)
- `root_page_id` - ID кореневої сторінки дерева
- `dry_run` - true/false (в тілі запиту)

## 🔄 Логіка роботи

### 1. Перевірка root page

```python
# Root page має бути в whitelist
allowed_ids = whitelist_manager.get_allowed_ids(space_key, confluence_client)

if root_page_id not in allowed_ids:
    return error: "Root page is not allowed by whitelist"
```

### 2. Збір дерева

```python
# Збираємо ВСЕ дерево
all_page_ids = collect_all_children(root_page_id)

# Фільтруємо через whitelist
pages_to_process = [p for p in all_page_ids if p in allowed_ids]
```

### 3. Обробка

```python
for page_id in pages_to_process:
    # Генеруємо теги
    # Записуємо якщо dry_run=false
```

## 📊 Режимна матриця

| Режим | Root check | Tree scope | dry_run=true | dry_run=false | Записи |
|-------|-----------|------------|--------------|---------------|--------|
| **TEST** | ✅ Whitelist | Whitelist | Симуляція | Симуляція | ❌ Ніколи |
| **SAFE_TEST** | ✅ Whitelist | Whitelist | Симуляція | Реальний | ✅ Якщо dry_run=false |
| **PROD** | ✅ Whitelist | Whitelist | Симуляція | Реальний | ✅ Якщо dry_run=false |

### Пояснення:

**Root check:**
- Завжди перевіряється що root_page_id ∈ allowed_ids
- Якщо ні → помилка, дерево не обробляється

**Tree scope:**
- Завжди фільтрується через allowed_ids
- Сторінки поза whitelist пропускаються

**Записи:**
- Контролюються параметром dry_run
- Режим (TEST/SAFE_TEST/PROD) не впливає на scope, тільки на дозволи запису

## 🆚 До/після

### До виправлення:

```python
# ❌ СТАРИЙ КОД
# Перевірка через .env
self.agent.enforce_root_policy(root_page_id)  # Використовує TAGGING_AGENT_TEST_TREE_ROOTS

# Обробка ВСЬОГО дерева
all_page_ids = collect_all_children(root_page_id)
for page_id in all_page_ids:  # Всі сторінки
    process(page_id)
```

### Після виправлення:

```python
# ✅ НОВИЙ КОД
# Перевірка через whitelist
allowed_ids = whitelist_manager.get_allowed_ids(space_key, confluence_client)

if root_page_id not in allowed_ids:
    return error

# Фільтрація дерева
all_page_ids = collect_all_children(root_page_id)
pages_to_process = [p for p in all_page_ids if p in allowed_ids]

for page_id in pages_to_process:  # Тільки whitelist
    process(page_id)
```

## 📝 Логування

**Нове логування:**

```
[TagTree] Starting tag-tree for root_page_id=100, mode=PROD, dry_run=false, space_key=MYSPACE
[TagTree] Whitelist enabled for space=MYSPACE
[TagTree] Whitelist loaded: 5 allowed pages for MYSPACE
[TagTree] Allowed IDs (first 20): [100, 101, 102, 103, 104]
[TagTree] Root page 100 is in whitelist - allowed
[TagTree] Collected 10 total pages in tree
[TagTree] After whitelist filter: 5 to process, 5 skipped (not in whitelist)
[TagTree] Processing page 1/5: 100
[TagTree] Completed: 5 success, 0 errors, 0 skipped, 5 filtered by whitelist
```

## 📤 Відповідь API

**Нова структура:**

```json
{
  "status": "completed",
  "section": "domain-rehab-2-0",
  "allowed_labels": [...],
  "root_page_id": "100",
  "space_key": "MYSPACE",
  "total": 10,
  "processed": 5,
  "skipped_by_whitelist": 5,
  "success": 5,
  "errors": 0,
  "skipped_count": 0,
  "dry_run": false,
  "whitelist_enabled": true,
  "details": [
    {
      "page_id": "100",
      "title": "Root Page",
      "status": "updated",
      "tags": {...}
    }
  ]
}
```

**Нові поля:**
- `space_key` - простір для whitelist
- `skipped_by_whitelist` - кількість пропущених через whitelist
- `whitelist_enabled` - чи активний whitelist

## 🚀 Приклади використання

### Конфігурація whitelist

**`whitelist_config.json`:**
```json
{
  "spaces": [
    {
      "space_key": "MYSPACE",
      "pages": [
        {"id": 100, "name": "Documentation Root", "root": true}
      ]
    }
  ]
}
```

### Запити

**TEST режим:**
```bash
curl -X POST "http://localhost:8000/bulk/tag-tree/MYSPACE/100" \
  -H "Content-Type: application/json" \
  -d '{"dry_run": true}'
```

**SAFE_TEST dry-run:**
```bash
curl -X POST "http://localhost:8000/bulk/tag-tree/MYSPACE/100" \
  -H "Content-Type: application/json" \
  -d '{"dry_run": true}'
```

**SAFE_TEST запис:**
```bash
curl -X POST "http://localhost:8000/bulk/tag-tree/MYSPACE/100" \
  -H "Content-Type: application/json" \
  -d '{"dry_run": false}'
```

**PROD запис:**
```bash
curl -X POST "http://localhost:8000/bulk/tag-tree/MYSPACE/100" \
  -H "Content-Type: application/json" \
  -d '{"dry_run": false}'
```

## ⚠️ Важливі зміни

### 1. Нова сигнатура

**Старий виклик не працюватиме:**
```bash
# ❌ Більше не працює
POST /bulk/tag-tree/100
```

**Потрібен space_key:**
```bash
# ✅ Правильно
POST /bulk/tag-tree/MYSPACE/100
```

### 2. Root page validation

**Якщо root page не в whitelist:**
```json
{
  "status": "error",
  "message": "Root page 100 is not allowed by whitelist for space MYSPACE",
  "total": 0,
  "whitelist_enabled": true,
  "root_page_allowed": false
}
```

### 3. Whitelist обов'язковий

Якщо немає entry points:
```json
{
  "status": "error",
  "message": "No whitelist entries for space MYSPACE. Add entries to whitelist_config.json"
}
```

## 🧪 Тести

**Додано нові тести в `test_tag_tree_whitelist_integration.py`:**

1. `test_tag_tree_root_in_whitelist` - root в whitelist
2. `test_tag_tree_root_not_in_whitelist` - root не в whitelist (помилка)
3. `test_tag_tree_safe_test_dry_run` - SAFE_TEST + dry_run
4. `test_tag_tree_safe_test_real_write` - SAFE_TEST + запис
5. `test_tag_tree_prod_dry_run_uses_whitelist` - PROD з whitelist

**Результати:**
```
✅ Всі нові тести проходять
✅ Базові тести не зламані
✅ tag-space продовжує працювати
```

## ✅ Що НЕ змінилось

- ✅ Section detection - працює як раніше
- ✅ allowed_labels логіка - збережена
- ✅ Tag generation - без змін
- ✅ Режимна матриця для запису - збережена
- ✅ Інші ендпоінти - не змінені

## 📚 Файли

**Змінено:**
- `src/services/bulk_tagging_service.py` - додано whitelist integration
- `src/api/routers/bulk_tagging_router.py` - оновлена сигнатура

**Тести:**
- `tests/test_tag_tree_whitelist_integration.py` - нові тести

**Документація:**
- `docs/TAG_TREE_WHITELIST.md` - цей документ

## 🔍 Міграція

**Якщо використовуєте tag-tree:**

1. **Додайте space_key до URL:**
   ```
   /bulk/tag-tree/{space_key}/{root_page_id}
   ```

2. **Додайте root page до whitelist_config.json:**
   ```json
   {
     "spaces": [
       {
         "space_key": "YOUR_SPACE",
         "pages": [
           {"id": YOUR_ROOT_ID, "name": "Root", "root": true}
         ]
       }
     ]
   }
   ```

3. **Перевірте що всі потрібні сторінки в піддереві:**
   - Якщо root в whitelist → його діти автоматично дозволені
   - Якщо потрібна тільки частина дерева → додайте тільки потрібні entry points

## 🎯 Переваги

1. **Консистентність** - tag-tree і tag-space використовують один механізм
2. **Безпека** - не можна обробити дерево поза whitelist
3. **Контроль** - всі дозволи в одному файлі (whitelist_config.json)
4. **Прозорість** - зрозуміла режимна матриця
5. **Гнучкість** - dry_run керує записом незалежно від scope
