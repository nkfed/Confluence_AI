# Tag-Tree Endpoint Documentation

## Ендпоінт

```
POST /bulk/tag-tree/{space_key}/{root_page_id}
```

## Опис

Тегує дерево сторінок Confluence, починаючи з кореневої сторінки, з контролем через whitelist.

## Параметри

### Path Parameters

| Параметр | Тип | Обов'язковий | Опис |
|----------|-----|--------------|------|
| `space_key` | string | ✅ Так | Ключ Confluence простору (для whitelist lookup) |
| `root_page_id` | string | ✅ Так | ID кореневої сторінки дерева |

### Body Parameters

| Параметр | Тип | Обов'язковий | За замовчуванням | Опис |
|----------|-----|--------------|------------------|------|
| `dry_run` | boolean | ❌ Ні | `true` | Якщо true, симулює тегування без запису |

## Whitelist Integration

**Ендпоінт використовує `whitelist_config.json` для контролю доступу:**

1. Завантажує whitelist для `space_key`
2. Перевіряє що `root_page_id` є в whitelist
3. Збирає дерево сторінок
4. Фільтрує через whitelist (обробляє тільки дозволені сторінки)

## Режимна матриця

| Режим | Root перевірка | Tree scope | dry_run=true | dry_run=false | Записи |
|-------|----------------|------------|--------------|---------------|--------|
| **TEST** | Whitelist | Whitelist | Симуляція | Симуляція | ❌ Ніколи |
| **SAFE_TEST** | Whitelist | Whitelist | Симуляція | Реальний | ✅ Якщо dry_run=false |
| **PROD** | Whitelist | Whitelist | Симуляція | Реальний | ✅ Якщо dry_run=false |

## Приклади запитів

### 1. Dry-run в TEST режимі

```bash
curl -X POST \
  http://localhost:8000/bulk/tag-tree/nkfedba/19699862097 \
  -H 'Content-Type: application/json' \
  -d '{"dry_run": true}'
```

**Відповідь:**
```json
{
  "status": "completed",
  "space_key": "nkfedba",
  "root_page_id": "19699862097",
  "total": 10,
  "processed": 5,
  "skipped_by_whitelist": 5,
  "success": 5,
  "errors": 0,
  "dry_run": true,
  "whitelist_enabled": true,
  "details": [
    {
      "page_id": "19699862097",
      "title": "Root Page",
      "status": "dry_run",
      "tags": {
        "proposed": ["domain-rehab-2-0", "doc-tech"],
        "existing": [],
        "to_add": ["domain-rehab-2-0", "doc-tech"]
      }
    }
  ]
}
```

### 2. Реальний запис в SAFE_TEST

```bash
curl -X POST \
  http://localhost:8000/bulk/tag-tree/nkfedba/19699862097 \
  -H 'Content-Type: application/json' \
  -d '{"dry_run": false}'
```

**Відповідь:**
```json
{
  "status": "completed",
  "space_key": "nkfedba",
  "root_page_id": "19699862097",
  "total": 10,
  "processed": 5,
  "skipped_by_whitelist": 5,
  "success": 5,
  "errors": 0,
  "dry_run": false,
  "whitelist_enabled": true,
  "details": [
    {
      "page_id": "19699862097",
      "title": "Root Page",
      "status": "updated",
      "tags": {
        "proposed": ["domain-rehab-2-0", "doc-tech"],
        "existing": [],
        "added": ["domain-rehab-2-0", "doc-tech"]
      }
    }
  ]
}
```

### 3. Root page не в whitelist

```bash
curl -X POST \
  http://localhost:8000/bulk/tag-tree/nkfedba/99999999 \
  -H 'Content-Type: application/json' \
  -d '{"dry_run": true}'
```

**Відповідь:**
```json
{
  "status": "error",
  "message": "Root page 99999999 is not allowed by whitelist for space nkfedba",
  "total": 0,
  "processed": 0,
  "errors": 1,
  "whitelist_enabled": true,
  "root_page_allowed": false
}
```

### 4. Простір без whitelist entries

```bash
curl -X POST \
  http://localhost:8000/bulk/tag-tree/UNKNOWN/19699862097 \
  -H 'Content-Type: application/json' \
  -d '{"dry_run": true}'
```

**Відповідь:**
```json
{
  "status": "error",
  "message": "No whitelist entries for space UNKNOWN. Add entries to whitelist_config.json",
  "total": 0,
  "processed": 0,
  "errors": 1
}
```

## Структура відповіді

### Успішна відповідь

```json
{
  "status": "completed",
  "section": "domain-rehab-2-0",
  "allowed_labels": ["domain-rehab-2-0", "doc-tech", "doc-user"],
  "root_page_id": "19699862097",
  "space_key": "nkfedba",
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
      "page_id": "19699862097",
      "title": "Page Title",
      "status": "updated",
      "skipped": false,
      "tags": {
        "proposed": ["domain-rehab-2-0"],
        "existing": [],
        "to_add": [],
        "added": ["domain-rehab-2-0"]
      },
      "dry_run": false
    }
  ],
  "skipped_pages": []
}
```

### Поля відповіді

| Поле | Тип | Опис |
|------|-----|------|
| `status` | string | "completed" або "error" |
| `section` | string | Виявлена секція документації |
| `allowed_labels` | array | Дозволені теги для цієї секції |
| `root_page_id` | string | ID кореневої сторінки |
| `space_key` | string | Ключ простору |
| `total` | number | Загальна кількість сторінок у дереві |
| `processed` | number | Кількість оброблених сторінок (після фільтрації) |
| `skipped_by_whitelist` | number | Кількість пропущених через whitelist |
| `success` | number | Кількість успішно оброблених |
| `errors` | number | Кількість помилок |
| `skipped_count` | number | Кількість пропущених (no changes) |
| `dry_run` | boolean | Чи це був dry-run |
| `whitelist_enabled` | boolean | Чи активний whitelist |
| `details` | array | Деталі по кожній сторінці |
| `skipped_pages` | array | Список пропущених сторінок |

### Поля detail об'єкта

| Поле | Тип | Опис |
|------|-----|------|
| `page_id` | string | ID сторінки |
| `title` | string | Назва сторінки |
| `status` | string | "updated", "dry_run", "no_changes", або "error" |
| `skipped` | boolean | Чи пропущена сторінка |
| `tags` | object | Структура тегів |
| `dry_run` | boolean | Чи це був dry-run |

### Структура tags

| Поле | Тип | Опис |
|------|-----|------|
| `proposed` | array | AI-згенеровані теги |
| `existing` | array | Існуючі теги на сторінці |
| `to_add` | array | Теги до додавання (dry_run) |
| `added` | array | Фактично додані теги (real update) |

## Коди помилок

| Код | Опис | Приклад |
|-----|------|---------|
| 200 | Успішно | Дерево оброблено |
| 400 | Неправильний запит | Невалідний space_key |
| 403 | Заборонено | Root page не в whitelist |
| 404 | Не знайдено | Сторінка не існує |
| 500 | Внутрішня помилка | Помилка сервера |

## Конфігурація Whitelist

**Файл: `whitelist_config.json`**

```json
{
  "spaces": [
    {
      "space_key": "nkfedba",
      "description": "Особистий робочий простір",
      "pages": [
        {
          "id": 19699862097,
          "name": "Особисті нотатки бізнес-аналітика",
          "root": true
        },
        {
          "id": 19717193741,
          "name": "Функції Rovo-агентів"
        }
      ]
    }
  ]
}
```

**Правила:**
- `root: true` - entry point, його діти автоматично дозволені
- Без `root` - тільки конкретна сторінка (без дітей)
- Whitelist обов'язковий для всіх режимів

## Swagger UI

Ендпоінт доступний в Swagger UI за адресою:
```
http://localhost:8000/docs
```

**Форма параметрів:**
- `space_key` (path) - текстове поле, обов'язкове
- `root_page_id` (path) - текстове поле, обов'язкове
- `dry_run` (body) - checkbox, за замовчуванням true

## Python SDK Приклад

```python
import httpx

async def tag_tree_example():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/bulk/tag-tree/nkfedba/19699862097",
            json={"dry_run": False}
        )
        result = response.json()
        
        print(f"Status: {result['status']}")
        print(f"Processed: {result['processed']}/{result['total']}")
        print(f"Success: {result['success']}")
```

## Обмеження

1. **Whitelist обов'язковий** - без whitelist entries для space_key операція неможлива
2. **Root має бути в whitelist** - root_page_id повинен бути в allowed_ids
3. **Throttling** - 0.3 секунди між обробкою сторінок
4. **Таймаути** - 30 секунд на запит до Confluence API

## Troubleshooting

### Проблема: Root page not in whitelist

**Рішення:** Додайте root page до `whitelist_config.json`:
```json
{
  "space_key": "YOUR_SPACE",
  "pages": [
    {"id": YOUR_ROOT_ID, "name": "Root", "root": true}
  ]
}
```

### Проблема: No whitelist entries

**Рішення:** Створіть entry для space_key в `whitelist_config.json`

### Проблема: 404 Not Found

**Перевірте:**
- URL містить обидва параметри: `/{space_key}/{root_page_id}`
- `root_page_id` існує в Confluence
- Сервер запущений

### Проблема: Теги не записуються

**Перевірте:**
- `dry_run=false` в запиті
- Режим агента дозволяє запис (SAFE_TEST або PROD)
- Сторінка в whitelist

## Логування

```
[TagTree] Starting tag-tree for root_page_id=19699862097, mode=SAFE_TEST, dry_run=false, space_key=nkfedba
[TagTree] Whitelist loaded: 5 allowed pages for nkfedba
[TagTree] Root page 19699862097 is in whitelist - allowed
[TagTree] Collected 10 total pages in tree
[TagTree] After whitelist filter: 5 to process, 5 skipped
[TagTree] Processing page 1/5: 19699862097
[TagTree] Completed: 5 success, 0 errors, 0 skipped, 5 filtered by whitelist
```

## Дивіться також

- [WhitelistManager Documentation](WHITELIST_MANAGER.md)
- [Tag-Space Endpoint](TAG_SPACE_ENDPOINT.md)
- [Режимна матриця](AGENT_MODES.md)
