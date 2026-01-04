# Bulk Tagging System - Implementation Summary

## Огляд

Реалізовано повноцінну систему bulk-тегування просторів Confluence з підтримкою:
- 3 нові ендпоінти API
- Режимну логіку (TEST / SAFE_TEST / PROD)
- Фільтрацію сторінок
- Скидання тегів
- Уніфіковану структуру відповідей

## Нові компоненти

### API Ендпоінти

#### 1. GET /spaces
Отримання списку просторів Confluence з пагінацією.

**Параметри:**
- `query` (optional): Пошуковий запит
- `accessible_only` (default: true): Тільки доступні простори
- `start` (default: 0): Початковий індекс
- `limit` (default: 25): Максимальна кількість результатів

**Відповідь:**
```json
{
  "spaces": [
    {
      "id": "string",
      "key": "string",
      "name": "string",
      "type": "string",
      "status": "string"
    }
  ],
  "start": 0,
  "limit": 25,
  "size": 10,
  "total": 10
}
```

#### 2. POST /bulk/reset-tags/{space_key}
Скидання тегів на всіх сторінках простору.

**Параметри:**
- `space_key` (path): Ключ простору Confluence
- `categories` (query, optional): Категорії тегів для видалення (comma-separated: doc,domain,kb,tool)
- `dry_run` (query, default: true): Dry-run режим

**Відповідь:**
```json
{
  "total": 100,
  "processed": 100,
  "removed": 85,
  "no_tags": 10,
  "errors": 5,
  "dry_run": true,
  "details": [
    {
      "page_id": "string",
      "title": "string",
      "status": "removed" | "dry_run" | "no_tags" | "error",
      "removed_tags": ["doc-tech", "domain-helpdesk-site"],
      "skipped": false
    }
  ]
}
```

#### 3. POST /bulk/tag-space/{space_key}
Bulk-тегування всіх сторінок у просторі.

**Параметри:**
- `space_key` (path): Ключ простору
- `dry_run` (query, optional): Перевизначення режиму
- `exclude_archived` (query, default: true): Виключити архівовані
- `exclude_index_pages` (query, default: true): Виключити індексні
- `exclude_templates` (query, default: true): Виключити шаблони
- `exclude_empty_pages` (query, default: true): Виключити порожні
- `exclude_by_title_regex` (query, optional): Regex для виключення

**Відповідь:**
```json
{
  "total": 100,
  "processed": 85,
  "success": 80,
  "errors": 5,
  "skipped_count": 15,
  "dry_run": true,
  "mode": "SAFE_TEST",
  "details": [
    {
      "page_id": "string",
      "title": "string",
      "status": "updated" | "dry_run" | "forbidden" | "error",
      "tags": {
        "proposed": ["doc-tech", "kb-overview"],
        "existing": ["old-tag"],
        "to_add": ["doc-tech"],
        "added": [],
        "skipped": [],
        "errors": []
      }
    }
  ],
  "skipped_pages": [
    {
      "page_id": "string",
      "title": "string",
      "reason": "Page is archived"
    }
  ]
}
```

### Сервіси

#### PageFilterService
**Файл:** `src/services/page_filter_service.py`

Фільтрація сторінок за критеріями:
- `is_archived()` - архівовані сторінки
- `is_index_page()` - індексні сторінки
- `is_template()` - шаблони
- `is_empty()` - порожні сторінки (< 50 символів)
- `matches_title_regex()` - фільтрація за regex
- `is_allowed_in_safe_test()` - перевірка whitelist
- `should_exclude_page()` - універсальний метод

#### SpaceService
**Файл:** `src/services/space_service.py`

Робота з просторами Confluence:
- `get_spaces()` - отримання списку просторів
- `get_space_pages()` - отримання всіх сторінок простору

#### TagResetService
**Файл:** `src/services/tag_reset_service.py`

Скидання тегів:
- `is_ai_tag()` - визначення AI-тегів
- `filter_tags_by_categories()` - фільтрація за категоріями
- `reset_page_tags()` - скидання тегів на одній сторінці
- `reset_space_tags()` - скидання тегів на всіх сторінках простору

### Оркестратори

#### BulkTagOrchestrator
**Файл:** `src/core/bulk_tag_orchestrator.py`

Центральний компонент для bulk-тегування:
- Визначення режиму роботи (TEST/SAFE_TEST/PROD)
- Застосування фільтрів через PageFilterService
- Виклик TaggingAgent для кожної сторінки
- Контроль dry_run режиму
- Формування агрегованої відповіді
- Логування всіх етапів

**Режимна логіка:**

| Режим | dry_run | Whitelist | Запис |
|-------|---------|-----------|-------|
| TEST | Завжди true | Застосовується | Заборонено |
| SAFE_TEST (dry_run=true) | true | Застосовується | Заборонено |
| SAFE_TEST (dry_run=false) | false | Застосовується | Дозволено тільки для whitelist |
| PROD (dry_run=true) | true | Не застосовується | Заборонено |
| PROD (dry_run=false) | false | Не застосовується | Дозволено |

### Розширення ConfluenceClient

**Файл:** `src/clients/confluence_client.py`

Додано методи:
- `get_spaces()` - отримання списку просторів
- `get_pages_in_space()` - отримання всіх сторінок простору з expand
- `remove_labels()` - видалення тегів
- `add_labels()` - додавання тегів

## Тести

Створено комплексне покриття тестами:

### test_page_filter_service.py
- Тестування всіх фільтрів
- Режимна логіка
- Whitelist

### test_spaces_api.py
- Отримання просторів
- Пагінація
- Обробка помилок

### test_bulk_reset_tags.py
- Скидання тегів
- Фільтрація за категоріями
- Dry-run режим
- Обробка помилок

### test_bulk_tag_space.py (комплексний)
- Режимна логіка (TEST/SAFE_TEST/PROD)
- Dry-run режим
- Фільтрація сторінок (archived, index, template, empty, regex)
- Whitelist у SAFE_TEST
- Обмеження тегів (limit_tags_per_category)
- Обробка помилок AI та Confluence
- Уніфікована структура відповідей

## Використання

### Запуск API

```bash
# Активувати venv
.\.venv\Scripts\Activate.ps1

# Запустити сервер
python run_server.py
```

### Приклади запитів

#### Отримати список просторів
```bash
curl -X GET "http://localhost:8000/spaces?limit=10"
```

#### Скинути всі AI-теги у просторі (dry-run)
```bash
curl -X POST "http://localhost:8000/bulk/reset-tags/TEST?dry_run=true"
```

#### Скинути тільки doc-теги
```bash
curl -X POST "http://localhost:8000/bulk/reset-tags/TEST?categories=doc&dry_run=true"
```

#### Bulk-тегування простору (dry-run)
```bash
curl -X POST "http://localhost:8000/bulk/tag-space/TEST?dry_run=true"
```

#### Bulk-тегування з виключенням архівованих та індексних сторінок
```bash
curl -X POST "http://localhost:8000/bulk/tag-space/TEST?dry_run=false&exclude_archived=true&exclude_index_pages=true"
```

### Запуск тестів

```bash
# Всі тести
pytest tests/

# Конкретний тест
pytest tests/test_bulk_tag_space.py -v

# З покриттям
pytest tests/ --cov=src --cov-report=html
```

## Конфігурація

### Змінні середовища (.env)

```env
# Режим роботи агентів
AGENT_MODE=TEST  # TEST, SAFE_TEST, або PROD

# Whitelist для TAGGING_AGENT (comma-separated page IDs)
TAGGING_AGENT_TEST_PAGE=123456,789012

# Confluence
CONFLUENCE_BASE_URL=https://your-domain.atlassian.net
CONFLUENCE_EMAIL=your-email@example.com
CONFLUENCE_API_TOKEN=your-api-token

# OpenAI
OPENAI_API_KEY=your-openai-key
OPENAI_MODEL=gpt-4o
```

## Критерії приймання

✅ Всі три ендпоінти працюють згідно OpenAPI  
✅ Структура тегів уніфікована  
✅ Режими працюють коректно (TEST/SAFE_TEST/PROD)  
✅ Фільтри працюють коректно  
✅ /spaces повертає коректний список  
✅ /bulk/reset-tags видаляє теги згідно параметрів  
✅ Всі тести проходять  
✅ Код типізований  
✅ Логування та audit-trail працюють  
✅ Відповіді повністю відповідають OpenAPI  

## Архітектурні рішення

1. **Модульність**: Кожен компонент має чітку відповідальність
2. **Тестованість**: Mock-friendly дизайн з dependency injection
3. **Розширюваність**: Легко додати нові фільтри або режими
4. **Безпека**: Режимна логіка з whitelist та dry-run за замовчуванням
5. **Уніфікація**: Єдина структура тегів для всіх ендпоінтів
6. **Логування**: Повний audit trail всіх операцій

## Можливі розширення

1. **Паралельна обробка** - використати asyncio.gather для одночасного тегування
2. **Прогрес-бар** - WebSocket для real-time оновлень прогресу
3. **Schedulе** - планування bulk-операцій через celery/APScheduler
4. **Rollback** - можливість відкату змін
5. **Звіти** - детальні звіти по результатам bulk-операцій
6. **Кешування** - кешування просторів та сторінок
