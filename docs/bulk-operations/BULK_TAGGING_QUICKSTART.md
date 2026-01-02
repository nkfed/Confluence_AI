# Bulk Tagging - Quick Start Guide

## Швидкий старт

### 1. Переглянути доступні простори

```bash
curl -X GET "http://localhost:8000/spaces?limit=10"
```

**Відповідь:**
```json
{
  "spaces": [
    {"id": "1", "key": "TEST", "name": "Test Space", "type": "global", "status": "current"},
    {"id": "2", "key": "DOCS", "name": "Documentation", "type": "global", "status": "current"}
  ],
  "start": 0,
  "limit": 10,
  "size": 2,
  "total": 2
}
```

---

### 2. Dry-run bulk-тегування (безпечно)

```bash
curl -X POST "http://localhost:8000/bulk/tag-space/TEST?dry_run=true"
```

**Що відбувається:**
- ✅ Аналізує всі сторінки простору
- ✅ Викликає AI для кожної сторінки
- ✅ Показує, які теги будуть додані
- ❌ НЕ додає теги реально

**Відповідь:**
```json
{
  "total": 50,
  "processed": 45,
  "success": 45,
  "errors": 0,
  "skipped_count": 5,
  "dry_run": true,
  "mode": "TEST",
  "details": [
    {
      "page_id": "123",
      "title": "My Page",
      "status": "dry_run",
      "tags": {
        "proposed": ["doc-tech", "kb-overview"],
        "existing": ["old-tag"],
        "to_add": ["doc-tech", "kb-overview"],
        "added": [],
        "skipped": [],
        "errors": []
      }
    }
  ],
  "skipped_pages": [
    {"page_id": "456", "title": "Archived Page", "reason": "Page is archived"}
  ]
}
```

---

### 3. Реальне bulk-тегування (PROD режим)

**⚠️ УВАГА: Це реально додасть теги!**

```bash
# Спочатку встановити PROD режим у .env
AGENT_MODE=PROD

# Запустити з dry_run=false
curl -X POST "http://localhost:8000/bulk/tag-space/TEST?dry_run=false"
```

---

### 4. Bulk-тегування з фільтрами

```bash
# Виключити архівовані, індексні та порожні сторінки
curl -X POST "http://localhost:8000/bulk/tag-space/TEST?dry_run=true&exclude_archived=true&exclude_index_pages=true&exclude_empty_pages=true"

# Виключити сторінки з "Archive" у назві
curl -X POST "http://localhost:8000/bulk/tag-space/TEST?dry_run=true&exclude_by_title_regex=^Archive"
```

---

### 5. Скидання тегів (dry-run)

```bash
# Переглянути які теги будуть видалені
curl -X POST "http://localhost:8000/bulk/reset-tags/TEST?dry_run=true"
```

**Відповідь:**
```json
{
  "total": 50,
  "processed": 50,
  "removed": 40,
  "no_tags": 5,
  "errors": 5,
  "dry_run": true,
  "details": [
    {
      "page_id": "123",
      "title": "My Page",
      "status": "dry_run",
      "removed_tags": ["doc-tech", "domain-helpdesk-site"],
      "skipped": false
    }
  ]
}
```

---

### 6. Скидання тільки певних категорій

```bash
# Видалити тільки doc-теги
curl -X POST "http://localhost:8000/bulk/reset-tags/TEST?categories=doc&dry_run=true"

# Видалити doc та domain теги
curl -X POST "http://localhost:8000/bulk/reset-tags/TEST?categories=doc,domain&dry_run=true"
```

---

### 7. SAFE_TEST режим (тестування на whitelist)

**У .env:**
```env
AGENT_MODE=SAFE_TEST
TAGGING_AGENT_TEST_PAGE=123456,789012  # Тільки ці сторінки
```

**Запуск:**
```bash
# Dry-run на whitelist сторінках
curl -X POST "http://localhost:8000/bulk/tag-space/TEST?dry_run=true"

# Реальний запис тільки на whitelist сторінках
curl -X POST "http://localhost:8000/bulk/tag-space/TEST?dry_run=false"
```

**Результат:**
- ✅ Обробить тільки сторінки з whitelist (123456, 789012)
- ❌ Пропустить всі інші сторінки

---

## Типові сценарії

### Сценарій 1: Перший раз тегую простір

1. Переглянути простори
```bash
curl -X GET "http://localhost:8000/spaces"
```

2. Dry-run на тестовому просторі
```bash
curl -X POST "http://localhost:8000/bulk/tag-space/TEST?dry_run=true"
```

3. Переглянути результат, переконатися що все правильно

4. Якщо все ОК — виконати реально
```bash
# У .env: AGENT_MODE=PROD
curl -X POST "http://localhost:8000/bulk/tag-space/TEST?dry_run=false"
```

---

### Сценарій 2: Оновити теги на всіх сторінках

1. Скинути старі теги (dry-run)
```bash
curl -X POST "http://localhost:8000/bulk/reset-tags/TEST?dry_run=true"
```

2. Скинути старі теги реально
```bash
curl -X POST "http://localhost:8000/bulk/reset-tags/TEST?dry_run=false"
```

3. Додати нові теги
```bash
curl -X POST "http://localhost:8000/bulk/tag-space/TEST?dry_run=false"
```

---

### Сценарій 3: Тегування тільки нових сторінок

1. Виключити сторінки, які вже мають теги (через custom logic)

2. Або використати фільтри для виключення певних сторінок
```bash
curl -X POST "http://localhost:8000/bulk/tag-space/TEST?dry_run=false&exclude_index_pages=true"
```

---

## Безпека

### Рекомендована послідовність

1. **TEST режим** (AGENT_MODE=TEST)
   - Завжди dry_run=true
   - Працює тільки з whitelist
   - Нічого не змінює

2. **SAFE_TEST режим** (AGENT_MODE=SAFE_TEST)
   - dry_run=true → симуляція
   - dry_run=false → запис тільки на whitelist
   - Безпечне тестування

3. **PROD режим** (AGENT_MODE=PROD)
   - Повний доступ
   - Використовувати обережно!

### Завжди починайте з dry_run=true!

```bash
# ✅ ДОБРЕ - спочатку перевірити
curl -X POST ".../tag-space/TEST?dry_run=true"

# Переглянути результат...

# ✅ ДОБРЕ - якщо все ОК, виконати реально
curl -X POST ".../tag-space/TEST?dry_run=false"
```

---

## Моніторинг

### Перевірити логи

```bash
# Windows
Get-Content logs/app.log -Tail 50 -Wait

# Linux/Mac
tail -f logs/app.log
```

### Структура відповіді

Всі bulk-операції повертають:
- `total` - всього сторінок у просторі
- `processed` - оброблено сторінок
- `success` - успішно оброблено
- `errors` - помилки
- `skipped_count` - пропущено фільтрами
- `dry_run` - чи був dry-run
- `mode` - поточний режим
- `details[]` - деталі по кожній сторінці
- `skipped_pages[]` - пропущені сторінки з причинами

---

## Troubleshooting

### Помилка: "Not allowed in SAFE_TEST mode"

**Причина:** Сторінка не у whitelist

**Рішення:**
1. Додати сторінку у whitelist у .env
2. Або перемкнутися на PROD режим

### Помилка: "AI Error"

**Причина:** OpenAI API недоступний або помилка

**Рішення:**
1. Перевірити OPENAI_API_KEY
2. Перевірити інтернет-з'єднання
3. Переглянути логи для деталей

### Помилка: "Confluence API Error"

**Причина:** Confluence API недоступний

**Рішення:**
1. Перевірити CONFLUENCE_BASE_URL
2. Перевірити CONFLUENCE_API_TOKEN
3. Перевірити права доступу

---

## Корисні команди

```bash
# Запустити тести
pytest tests/test_bulk_tag_space.py -v

# Перевірити структуру відповіді
curl -X POST "http://localhost:8000/bulk/tag-space/TEST?dry_run=true" | jq .

# Отримати тільки успішні
curl -X POST "http://localhost:8000/bulk/tag-space/TEST?dry_run=true" | jq '.details[] | select(.status == "dry_run")'

# Підрахувати помилки
curl -X POST "http://localhost:8000/bulk/tag-space/TEST?dry_run=true" | jq '.errors'
```
