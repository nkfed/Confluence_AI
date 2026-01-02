# ✅ Стандартизовано: Респонс `reset-tags` для dry_run режиму

## 🎯 Проблема

Попередня реалізація `reset-tags` некоректно відображала результати у dry_run режимі:
- Поле `removed` показувало кількість сторінок, які _були б_ оброблені, навіть при `dry_run=true`
- У `details[]` поле `removed_tags` містило теги, які _не були_ фактично видалені
- Неможливо було відрізнити dry_run від реального видалення без перевірки поля `dry_run`

## ✅ Рішення

Стандартизовано структуру респонсу для чіткого розділення dry_run та реального видалення.

### Нова структура відповіді

#### 🔵 dry_run=true (симуляція)

**Кореневі поля:**
```json
{
  "removed": 0,        // ← завжди 0 при dry_run
  "to_remove": 5,      // ← кількість що буде видалено
  "dry_run": true
}
```

**Details поля:**
```json
{
  "page_id": "123",
  "title": "Page Title",
  "status": "dry_run",
  "to_remove_tags": ["doc-api", "kb-guide"],  // ← теги що будуть видалені
  "skipped": false
}
```

#### 🟢 dry_run=false (реальне видалення)

**Кореневі поля:**
```json
{
  "removed": 5,        // ← фактична кількість видалених
  "dry_run": false
  // to_remove не передається
}
```

**Details поля:**
```json
{
  "page_id": "123",
  "title": "Page Title",
  "status": "removed",
  "removed_tags": ["doc-api", "kb-guide"],  // ← фактично видалені теги
  "skipped": false
}
```

#### ⚪ no_tags (немає тегів для видалення)

**dry_run=true:**
```json
{
  "status": "no_tags",
  "to_remove_tags": []  // ← порожній список
}
```

**dry_run=false:**
```json
{
  "status": "no_tags",
  "removed_tags": []  // ← порожній список
}
```

## 📊 Порівняння

| Характеристика | dry_run=true | dry_run=false |
|----------------|--------------|---------------|
| **Корінь:** `removed` | `0` | Фактична кількість |
| **Корінь:** `to_remove` | Кількість для видалення | Не передається |
| **Details:** теги | `to_remove_tags` | `removed_tags` |
| **Details:** `status` | `"dry_run"` | `"removed"` |

## 🔧 Технічні зміни

### 1. `src/services/tag_reset_service.py`

#### `reset_page_tags()` метод

**Було:**
```python
if dry_run:
    return {
        "status": "dry_run",
        "removed_tags": tags_to_remove  # ❌ некоректна назва
    }
```

**Стало:**
```python
if dry_run:
    return {
        "status": "dry_run",
        "to_remove_tags": tags_to_remove  # ✅ правильна назва
    }
```

#### Summary методи (`reset_tree_tags`, `reset_space_tags`)

**Було:**
```python
summary = {
    "removed": removed_count,  # ❌ завжди показувало кількість
    "dry_run": dry_run
}
```

**Стало:**
```python
summary = {
    "dry_run": dry_run
}

if dry_run:
    summary["removed"] = 0           # ✅ завжди 0
    summary["to_remove"] = removed_count  # ✅ що буде видалено
else:
    summary["removed"] = removed_count   # ✅ фактично видалено
```

### 2. Оновлено тести

#### Нові тести у `tests/test_reset_tags_root_id.py`:

1. ✅ `test_dry_run_response_structure` — перевірка `to_remove_tags` при dry_run
2. ✅ `test_actual_removal_response_structure` — перевірка `removed_tags` при видаленні
3. ✅ `test_summary_removed_vs_to_remove` — перевірка summary полів

#### Оновлено існуючі тести:

- ✅ `test_reset_tags_space_scope_without_root_id`
- ✅ `test_reset_tags_tree_scope_with_root_id`
- ✅ `test_reset_tags_tree_scope_with_categories`
- ✅ `test_reset_page_tags_dry_run`
- ✅ `test_reset_page_tags_no_tags`
- ✅ `test_reset_page_tags_category_filter`
- ✅ `test_reset_space_tags`

## 🧪 Результати тестування

```bash
$ pytest tests/test_reset_tags_root_id.py tests/test_bulk_reset_tags.py -v

✅ 19/19 tests passed

Нові тести:
- test_dry_run_response_structure ✅
- test_actual_removal_response_structure ✅
- test_summary_removed_vs_to_remove ✅

Загалом з expand тестами:
✅ 25/25 tests passed
```

## 💡 Приклади використання

### 1. Dry-run для перевірки (space scope)

**Request:**
```bash
POST /bulk/reset-tags/MYSPACE?dry_run=true
```

**Response:**
```json
{
  "total": 10,
  "processed": 10,
  "removed": 0,          // ← 0 при dry_run
  "to_remove": 8,        // ← що буде видалено
  "no_tags": 2,
  "errors": 0,
  "dry_run": true,
  "scope": "space",
  "root_id": null,
  "details": [
    {
      "page_id": "123",
      "title": "Page 1",
      "status": "dry_run",
      "to_remove_tags": ["doc-api", "kb-guide"],  // ← що буде видалено
      "skipped": false
    }
  ]
}
```

### 2. Реальне видалення (tree scope)

**Request:**
```bash
POST /bulk/reset-tags/DOCS?root_id=789&dry_run=false
```

**Response:**
```json
{
  "total": 5,
  "processed": 5,
  "removed": 4,          // ← фактично видалено
  "no_tags": 1,
  "errors": 0,
  "dry_run": false,
  "scope": "tree",
  "root_id": "789",
  "details": [
    {
      "page_id": "790",
      "title": "Child Page",
      "status": "removed",
      "removed_tags": ["doc-tech", "domain-backend"],  // ← фактично видалені
      "skipped": false
    }
  ]
}
```

### 3. Порівняння: Спочатку dry_run, потім виконання

```bash
# Крок 1: Перевірка (dry_run)
POST /bulk/reset-tags/TEST?root_id=123&dry_run=true

Response:
{
  "removed": 0,
  "to_remove": 5,  // ← 5 сторінок будуть оброблені
  "dry_run": true
}

# Крок 2: Виконання (якщо все ОК)
POST /bulk/reset-tags/TEST?root_id=123&dry_run=false

Response:
{
  "removed": 5,  // ← 5 сторінок фактично оброблено
  "dry_run": false
}
```

## 🎯 Переваги нової структури

1. ✅ **Чіткість** — одразу видно, чи були теги видалені реально
2. ✅ **Узгодженість** — використовуються різні назви полів для різних режимів
3. ✅ **Безпека** — `removed=0` при dry_run запобігає плутанині
4. ✅ **Інформативність** — `to_remove` показує що буде зроблено
5. ✅ **Стандартизація** — відповідає best practices для API з dry_run режимом

## 🔄 Міграція

### Для клієнтів API

Якщо ви раніше використовували:
```javascript
// ❌ Старий код
if (response.dry_run) {
  console.log(`Would remove: ${response.removed} pages`);  // некоректно
}
```

Оновіть на:
```javascript
// ✅ Новий код
if (response.dry_run) {
  console.log(`Would remove: ${response.to_remove} pages`);
} else {
  console.log(`Removed: ${response.removed} pages`);
}

// Для details
response.details.forEach(page => {
  const tags = response.dry_run 
    ? page.to_remove_tags 
    : page.removed_tags;
  console.log(`Page ${page.page_id}: ${tags.join(', ')}`);
});
```

## 📁 Змінені файли

1. ✅ `src/services/tag_reset_service.py`
   - Оновлено `reset_page_tags()` — uses `to_remove_tags` for dry_run
   - Оновлено `reset_tree_tags()` — conditional `removed`/`to_remove` in summary
   - Оновлено `reset_space_tags()` — conditional `removed`/`to_remove` in summary

2. ✅ `tests/test_reset_tags_root_id.py`
   - Додано 3 нові тести для dry_run vs actual removal
   - Оновлено 7 існуючих тестів

3. ✅ `tests/test_bulk_reset_tags.py`
   - Оновлено 6 тестів для нової структури

## 🚀 Висновок

✅ **Респонс стандартизовано:**
- dry_run=true: `removed=0`, `to_remove=N`, `to_remove_tags`
- dry_run=false: `removed=N`, `removed_tags`
- Всі 25 тестів пройшли успішно
- Чітке розділення симуляції та реального видалення

---

**Дата:** 2025-12-30  
**Автор:** VS Code Agent  
**Версія:** 2.0  
**Статус:** ✅ Completed
