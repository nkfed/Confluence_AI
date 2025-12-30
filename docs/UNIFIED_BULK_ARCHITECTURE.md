# 🎯 Unified Bulk Endpoints Architecture v2.1

**Дата:** 2025-12-29  
**Версія:** 2.1  
**Статус:** Production Ready

---

## 📚 Огляд

Усі bulk-ендпоінти тепер використовують **уніфіковану архітектуру**:
- ✅ Єдина dry_run матриця для всіх режимів
- ✅ Обов'язковий whitelist-механізм через `WhitelistManager`
- ✅ Обов'язковий параметр `space_key`
- ✅ Уніфікована структура відповідей

---

## 🔷 Уніфікована dry_run матриця

**Для ВСІХ bulk-ендпоінтів:**

```python
if mode == "TEST":
    effective_dry_run = True  # Завжди симуляція
elif mode == "SAFE_TEST":
    effective_dry_run = dry_run if dry_run is not None else True
elif mode == "PROD":
    effective_dry_run = dry_run if dry_run is not None else True
else:
    effective_dry_run = True  # Fallback
```

| Режим | dry_run=true | dry_run=false | dry_run=None |
|-------|--------------|---------------|--------------|
| **TEST** | Симуляція | Симуляція (forced) | Симуляція (forced) |
| **SAFE_TEST** | Симуляція | Реальні зміни | Симуляція (default) |
| **PROD** | Симуляція | Реальні зміни | Симуляція (default) |

---

## 🔷 Whitelist-механізм

**Єдиний механізм для всіх ендпоінтів:**

```python
from src.core.whitelist.whitelist_manager import WhitelistManager

whitelist_manager = WhitelistManager()
allowed_ids = await whitelist_manager.get_allowed_ids(space_key, confluence_client)

# Фільтрація
filtered_ids = [pid for pid in page_ids if pid in allowed_ids]

# Перевірка
if not filtered_ids:
    return 403  # No pages allowed by whitelist
```

**Конфігурація:** `src/core/whitelist/whitelist_config.json`

---

## 🌐 Ендпоінти

### 1. POST `/bulk/tag-pages`

**Призначення:** Тегування списку сторінок

**Request:**
```json
{
  "space_key": "nkfedba",
  "page_ids": ["19699862097", "19729285121"],
  "dry_run": false
}
```

**Response:**
```json
{
  "total": 2,
  "processed": 2,
  "success": 2,
  "errors": 0,
  "skipped_by_whitelist": 0,
  "mode": "SAFE_TEST",
  "dry_run": false,
  "whitelist_enabled": true,
  "details": [...]
}
```

**Документація:** [TAG_PAGES_ENDPOINT.md](TAG_PAGES_ENDPOINT.md)

---

### 2. POST `/bulk/tag-tree/{space_key}/{root_page_id}`

**Призначення:** Тегування дерева сторінок

**Parameters:**
- `space_key` (path, required): Ключ простору
- `root_page_id` (path, required): ID кореневої сторінки
- `dry_run` (query, optional): Режим симуляції

**Response:**
```json
{
  "status": "completed",
  "space_key": "nkfedba",
  "root_page_id": "19699862097",
  "total": 10,
  "processed": 8,
  "skipped_by_whitelist": 2,
  "success": 8,
  "errors": 0,
  "dry_run": false,
  "whitelist_enabled": true,
  "details": [...]
}
```

**Документація:** [TAG_TREE_ENDPOINT.md](TAG_TREE_ENDPOINT.md)

---

### 3. POST `/bulk/tag-space/{space_key}`

**Призначення:** Тегування всього простору

**Parameters:**
- `space_key` (path, required): Ключ простору
- `dry_run` (query, optional): Режим симуляції
- `exclude_archived` (query, optional): Виключити архівні сторінки
- `exclude_index_pages` (query, optional): Виключити індексні сторінки
- `exclude_templates` (query, optional): Виключити шаблони
- `exclude_empty_pages` (query, optional): Виключити порожні сторінки
- `exclude_by_title_regex` (query, optional): Виключити за regex заголовка

**Response:**
```json
{
  "total": 100,
  "processed": 80,
  "success": 75,
  "errors": 5,
  "skipped_by_whitelist": 20,
  "mode": "SAFE_TEST",
  "dry_run": false,
  "whitelist_enabled": true,
  "details": [...]
}
```

**Документація:** [TAG_SPACE_ENDPOINT.md](TAG_SPACE_ENDPOINT.md)

---

### 4. POST `/pages/{page_id}/auto-tag`

**Призначення:** Автоматичне тегування однієї сторінки

**Parameters:**
- `page_id` (path, required): ID сторінки
- `space_key` (query, optional): Ключ простору для whitelist перевірки
- `dry_run` (query, optional): Режим симуляції

**Response:**
```json
{
  "status": "updated",
  "page_id": "19699862097",
  "mode": "SAFE_TEST",
  "dry_run": false,
  "whitelist_enabled": false,
  "tags": {
    "proposed": ["doc-tech", "domain-helpdesk"],
    "existing": ["old-tag"],
    "added": ["doc-tech", "domain-helpdesk"],
    "to_add": []
  }
}
```

**Документація:** [AUTO_TAG_ENDPOINT.md](AUTO_TAG_ENDPOINT.md)

---

## 🔧 Структура відповідей

### Bulk ендпоінти (tag-pages, tag-tree, tag-space):

```typescript
{
  // Основна інформація
  "status"?: string,              // Для tag-tree
  "space_key"?: string,           // Для tag-tree, tag-space
  "root_page_id"?: string,        // Для tag-tree
  
  // Статистика
  "total": number,                // Загальна кількість сторінок
  "processed": number,            // Оброблено (після whitelist)
  "success": number,              // Успішно
  "errors": number,               // Помилки
  "skipped_by_whitelist": number, // Пропущено через whitelist
  
  // Режим і стан
  "mode": string,                 // TEST | SAFE_TEST | PROD
  "dry_run": boolean,             // Чи була симуляція
  "whitelist_enabled": boolean,   // Чи був whitelist активний
  
  // Деталі
  "details": Array<{
    "page_id": string,
    "title"?: string,
    "status": string,             // updated | dry_run | error | skipped
    "tags": {
      "proposed": string[],
      "existing": string[],
      "added": string[],
      "to_add": string[]
    },
    "dry_run": boolean,
    "message"?: string
  }>,
  
  "skipped_pages"?: Array<{...}>  // Для tag-tree
}
```

### Single-page ендпоінт (auto-tag):

```typescript
{
  "status": string,               // updated | dry_run | forbidden | error
  "page_id": string,
  "mode": string,
  "dry_run": boolean,
  "whitelist_enabled": boolean,
  "message"?: string,
  "tags": {
    "proposed": string[],
    "existing": string[],
    "added": string[],
    "to_add": string[]
  } | null
}
```

---

## 🛡️ Безпека

### Whitelist обов'язковий

Всі bulk-ендпоінти вимагають whitelist:

1. **tag-pages:** Фільтрує `page_ids` через `allowed_ids`
2. **tag-tree:** Фільтрує дерево через `allowed_ids`
3. **tag-space:** Фільтрує простір через `allowed_ids`
4. **auto-tag:** Опціональна перевірка через `space_key`

### Помилки whitelist

- **403 Forbidden:** Якщо whitelist порожній або всі сторінки заборонені
- **500 Internal Error:** Якщо не вдалося завантажити whitelist

---

## 📖 Приклади використання

### Dry-run у TEST режимі:

```bash
export TAGGING_AGENT_MODE=TEST

curl -X POST http://localhost:8000/bulk/tag-pages \
  -H 'Content-Type: application/json' \
  -d '{
    "space_key": "nkfedba",
    "page_ids": ["19699862097"],
    "dry_run": false
  }'
# Результат: dry_run=true (forced)
```

### Реальні зміни у SAFE_TEST:

```bash
export TAGGING_AGENT_MODE=SAFE_TEST

curl -X POST http://localhost:8000/bulk/tag-pages \
  -H 'Content-Type: application/json' \
  -d '{
    "space_key": "nkfedba",
    "page_ids": ["19699862097"],
    "dry_run": false
  }'
# Результат: dry_run=false (real changes)
```

### Tag-tree з whitelist:

```bash
curl -X POST "http://localhost:8000/bulk/tag-tree/nkfedba/19699862097?dry_run=true"
# Тегує тільки сторінки з whitelist
```

### Auto-tag з whitelist:

```bash
curl -X POST "http://localhost:8000/pages/19699862097/auto-tag?space_key=nkfedba&dry_run=false"
# Перевіряє whitelist якщо space_key надано
```

---

## 🧪 Тестування

### Запуск тестів:

```bash
# Bulk endpoints
pytest tests/test_tag_pages_modes.py -v
pytest tests/test_tag_tree_modes.py -v
pytest tests/test_bulk_tag_space.py -v

# Auto-tag
pytest tests/test_auto_tag*.py -v
```

### Перевірка whitelist:

```bash
# Перевірити що сторінка в whitelist
pytest tests/test_tag_pages_modes.py::test_tag_pages_whitelist_filters_pages -v

# Перевірити 403 для порожнього whitelist
pytest tests/test_tag_pages_modes.py::test_tag_pages_no_whitelist_entries_returns_403 -v
```

---

## 🔄 Міграція з старої версії

### Що змінилося:

1. **Видалено дублікат `/bulk/tag-space`** з `bulk.py` (залишився в `bulk_tag_space.py`)
2. **`space_key` тепер обов'язковий** в `tag_tree()`
3. **Уніфіковано dry_run логіку** в `tag_space()` 
4. **Видалено deprecated модель** `BulkTagRequest`
5. **Переміщено в deprecated:** `bulk_tagging_router.py`
6. **Додано whitelist і режими** в `auto-tag`

### Що робити:

- ✅ Оновіть всі виклики `tag_tree()` — додайте `space_key`
- ✅ Перевірте whitelist конфігурацію в `whitelist_config.json`
- ✅ Протестуйте dry_run матрицю для кожного режиму
- ✅ Перевірте що `/bulk/tag-space` використовує розширену версію

---

## 📞 Підтримка

**Документація:**
- [TAG_PAGES_ENDPOINT.md](TAG_PAGES_ENDPOINT.md)
- [TAG_TREE_ENDPOINT.md](TAG_TREE_ENDPOINT.md)
- [TAG_SPACE_ENDPOINT.md](TAG_SPACE_ENDPOINT.md)
- [AUTO_TAG_ENDPOINT.md](AUTO_TAG_ENDPOINT.md)
- [WHITELIST_MECHANISM.md](WHITELIST_MECHANISM.md)

**Аудит:**
- [BULK_ENDPOINTS_AUDIT_REPORT.md](BULK_ENDPOINTS_AUDIT_REPORT.md)

---

**Версія:** 2.1  
**Дата:** 2025-12-29  
**Автор:** VS Code Agent
