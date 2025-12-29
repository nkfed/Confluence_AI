# 📘 Ендпоінт `/bulk/tag-pages` — API документація

## Загальний опис

Ендпоінт `/bulk/tag-pages` дозволяє тегувати список Confluence сторінок за їх ID з підтримкою whitelist-механізму та режимної логіки.

---

## 🔷 Метод

```http
POST /bulk/tag-pages
```

---

## 🔷 Тіло запиту (JSON)

```json
{
  "space_key": "nkfedba",
  "page_ids": ["19699862097", "19729285121"],
  "dry_run": false
}
```

### Параметри:

| Параметр     | Тип           | Обов'язковий | Опис                                                    |
|--------------|---------------|--------------|--------------------------------------------------------|
| `space_key`  | `string`      | ✅ Так       | Ключ Confluence простору (для whitelist lookup)        |
| `page_ids`   | `List[str]`   | ✅ Так       | Список ID сторінок для тегування                       |
| `dry_run`    | `bool`        | ❌ Ні        | `true` = симуляція, `false` = реальні зміни (default: `true`) |

---

## 🔷 Відповідь

### Успішна відповідь (200 OK):

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
  "details": [
    {
      "page_id": "19699862097",
      "status": "updated",
      "tags": {
        "proposed": ["doc-tech", "domain-helpdesk"],
        "existing": ["old-tag"],
        "added": ["doc-tech", "domain-helpdesk"],
        "to_add": []
      },
      "dry_run": false
    },
    {
      "page_id": "19729285121",
      "status": "updated",
      "tags": {
        "proposed": ["doc-business"],
        "existing": [],
        "added": ["doc-business"],
        "to_add": []
      },
      "dry_run": false
    }
  ]
}
```

### Помилки:

#### 403 Forbidden — Whitelist порожній:
```json
{
  "detail": "No whitelist entries for space nkfedba. Add entries to whitelist_config.json"
}
```

#### 403 Forbidden — Усі сторінки поза whitelist:
```json
{
  "detail": "No pages allowed by whitelist. Check whitelist_config.json"
}
```

#### 500 Internal Server Error — Помилка whitelist:
```json
{
  "detail": "Failed to load whitelist: <error message>"
}
```

---

## 🔷 Режимна логіка (Mode Control)

Поведінка `dry_run` залежить від режиму `TAGGING_AGENT_MODE`:

| Режим         | dry_run=true       | dry_run=false          | Опис                                  |
|---------------|--------------------|------------------------|---------------------------------------|
| **TEST**      | ✅ Симуляція       | ✅ Симуляція (forced)  | Завжди dry-run, реальні зміни заборонені |
| **SAFE_TEST** | ✅ Симуляція       | ✅ Реальні зміни       | dry_run керує поведінкою              |
| **PROD**      | ✅ Симуляція       | ✅ Реальні зміни       | dry_run керує поведінкою              |

---

## 🔷 Whitelist інтеграція

Ендпоінт **завжди** використовує whitelist для фільтрації сторінок:

1. Завантажує дозволені ID з `whitelist_config.json` для вказаного `space_key`
2. Фільтрує `page_ids`: обробляє **тільки** сторінки, які є в whitelist
3. Повертає `skipped_by_whitelist` — кількість пропущених сторінок
4. Якщо whitelist порожній або усі `page_ids` поза whitelist → **403 Forbidden**

### Приклад whitelist_config.json:

```json
{
  "nkfedba": {
    "entry_points": [19699862097, 19729285121],
    "include_children": true
  }
}
```

---

## 🔷 Приклади використання

### 1. Dry-run у TEST режимі (завжди симуляція):

```bash
export TAGGING_AGENT_MODE=TEST

curl -X POST \
  http://localhost:8000/bulk/tag-pages \
  -H 'Content-Type: application/json' \
  -d '{
    "space_key": "nkfedba",
    "page_ids": ["19699862097", "19729285121"],
    "dry_run": false
  }'
```

**Результат:** `dry_run: true` (forced), жодних змін

---

### 2. Реальні зміни у SAFE_TEST режимі:

```bash
export TAGGING_AGENT_MODE=SAFE_TEST

curl -X POST \
  http://localhost:8000/bulk/tag-pages \
  -H 'Content-Type: application/json' \
  -d '{
    "space_key": "nkfedba",
    "page_ids": ["19699862097", "19729285121"],
    "dry_run": false
  }'
```

**Результат:** `dry_run: false`, реальні зміни на whitelist сторінках

---

### 3. Фільтрація whitelist:

```bash
curl -X POST \
  http://localhost:8000/bulk/tag-pages \
  -H 'Content-Type: application/json' \
  -d '{
    "space_key": "nkfedba",
    "page_ids": ["19699862097", "99999999"],
    "dry_run": true
  }'
```

**Результат:**
- `total: 2` (запитано)
- `processed: 1` (оброблено тільки 19699862097)
- `skipped_by_whitelist: 1` (99999999 поза whitelist)

---

## 🔷 Структура відповіді `details`

Кожна сторінка у `details` містить:

| Поле         | Тип      | Опис                                                    |
|--------------|----------|---------------------------------------------------------|
| `page_id`    | `string` | ID сторінки                                             |
| `status`     | `string` | `"dry_run"`, `"updated"`, `"error"`                     |
| `tags`       | `object` | Інформація про теги (proposed, existing, added, to_add) |
| `dry_run`    | `bool`   | Чи був це dry-run для цієї сторінки                     |
| `message`    | `string` | Повідомлення про помилку (якщо `status == "error"`)     |

---

## 🔷 Логування

Ендпоінт логує:

```
[TagPages] Starting tag-pages for space_key=nkfedba, mode=SAFE_TEST, dry_run_param=False, effective_dry_run=False
[TagPages] Whitelist loaded: 50 allowed pages for nkfedba
[TagPages] Whitelist filtering: requested=2, allowed=50, filtered=2
[TagPages] Processing 2 allowed pages (mode=SAFE_TEST, effective_dry_run=False, skipped=0)
[TagPages] Processing page 19699862097 (effective_dry_run=False)
[TagPages] Generated tags for 19699862097: {'doc': ['doc-tech'], ...}
[TagPages] Updating labels for page 19699862097: adding ['doc-tech']
[TagPages] Successfully updated labels for page 19699862097
[TagPages] Tagging completed: 2 success, 0 errors, 0 skipped
```

---

## 🔷 Порівняння з іншими ендпоінтами

| Ендпоінт        | Scope                  | Whitelist | Режимна логіка | Dry-run |
|-----------------|------------------------|-----------|----------------|---------|
| `/tag-pages`    | Список сторінок        | ✅ Так    | ✅ Уніфіковано | ✅ Так  |
| `/tag-space`    | Весь простір           | ✅ Так    | ✅ Уніфіковано | ✅ Так  |
| `/tag-tree`     | Дерево сторінок        | ✅ Так    | ✅ Уніфіковано | ✅ Так  |

---

## 🔷 Коли використовувати `/tag-pages`?

✅ **Використовуйте**, якщо:
- Потрібно тегувати конкретний список сторінок
- Маєте явний перелік ID сторінок
- Хочете контролювати точний набір сторінок

❌ **Не використовуйте**, якщо:
- Потрібно тегувати весь простір → `/tag-space`
- Потрібно тегувати дерево сторінок → `/tag-tree`

---

## 🔷 Безпека та best practices

1. **Завжди перевіряйте whitelist** перед продакшн запусками
2. **Починайте з `dry_run=true`** для верифікації
3. **Використовуйте TEST режим** для тестування
4. **Обмежуйте `page_ids`** (не більше 100 сторінок за раз)
5. **Моніторте логи** для відстеження помилок

---

## 🔷 Troubleshooting

### Проблема: 403 "No whitelist entries"
**Рішення:** Додайте entry points у `whitelist_config.json`:
```json
{
  "nkfedba": {
    "entry_points": [19699862097],
    "include_children": true
  }
}
```

### Проблема: 403 "No pages allowed by whitelist"
**Рішення:** Перевірте, що `page_ids` дійсно є в whitelist або додайте їх у entry points.

### Проблема: Зміни не застосовуються у TEST режимі
**Рішення:** TEST режим **завжди** використовує dry-run. Використовуйте SAFE_TEST або PROD.

---

**Версія:** 2.1  
**Останнє оновлення:** 2025-12-29
