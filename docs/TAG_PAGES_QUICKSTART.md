# 🚀 TAG-PAGES Quick Start

Швидкий старт для ендпоінту `/bulk/tag-pages` з whitelist-механізмом.

---

## 📋 Передумови

1. **Налаштований whitelist:**
   ```json
   // whitelist_config.json
   {
     "nkfedba": {
       "entry_points": [19699862097, 19729285121],
       "include_children": true
     }
   }
   ```

2. **Встановлений режим:**
   ```bash
   export TAGGING_AGENT_MODE=SAFE_TEST
   ```

3. **Запущений сервер:**
   ```bash
   uvicorn src.main:app --reload
   ```

---

## 🟢 Крок 1: Dry-run (безпечна перевірка)

```bash
curl -X POST http://localhost:8000/bulk/tag-pages \
  -H 'Content-Type: application/json' \
  -d '{
    "space_key": "nkfedba",
    "page_ids": ["19699862097", "19729285121"],
    "dry_run": true
  }'
```

**Очікуваний результат:**
```json
{
  "total": 2,
  "processed": 2,
  "success": 2,
  "errors": 0,
  "skipped_by_whitelist": 0,
  "mode": "SAFE_TEST",
  "dry_run": true,
  "whitelist_enabled": true,
  "details": [
    {
      "page_id": "19699862097",
      "status": "dry_run",
      "tags": {
        "proposed": ["doc-tech", "domain-helpdesk"],
        "existing": ["old-tag"],
        "added": [],
        "to_add": ["doc-tech", "domain-helpdesk"]
      },
      "dry_run": true
    }
  ]
}
```

---

## 🟢 Крок 2: Реальні зміни (SAFE_TEST або PROD)

```bash
curl -X POST http://localhost:8000/bulk/tag-pages \
  -H 'Content-Type: application/json' \
  -d '{
    "space_key": "nkfedba",
    "page_ids": ["19699862097", "19729285121"],
    "dry_run": false
  }'
```

**Результат:**
```json
{
  "total": 2,
  "processed": 2,
  "success": 2,
  "dry_run": false,
  "details": [
    {
      "page_id": "19699862097",
      "status": "updated",
      "tags": {
        "proposed": ["doc-tech"],
        "existing": [],
        "added": ["doc-tech"],
        "to_add": []
      },
      "dry_run": false
    }
  ]
}
```

---

## 🔴 Типові помилки

### Помилка: 403 "No whitelist entries"

**Причина:** Whitelist не налаштований для space_key

**Рішення:**
```json
// whitelist_config.json
{
  "your-space-key": {
    "entry_points": [123456],
    "include_children": true
  }
}
```

---

### Помилка: 403 "No pages allowed by whitelist"

**Причина:** Усі page_ids поза whitelist

**Рішення:**
1. Перевірте page_ids коректні
2. Додайте їх у entry_points:
   ```json
   {
     "nkfedba": {
       "entry_points": [19699862097, 19729285121],
       "include_children": true
     }
   }
   ```

---

## 🧪 Запуск тестів

```bash
pytest tests/test_tag_pages_modes.py -v
```

**Очікувані результати:**
```
test_tag_pages_test_mode_always_dry_run PASSED
test_tag_pages_safe_test_mode_respects_dry_run_true PASSED
test_tag_pages_safe_test_mode_respects_dry_run_false PASSED
test_tag_pages_prod_mode_respects_dry_run_true PASSED
test_tag_pages_prod_mode_respects_dry_run_false PASSED
test_tag_pages_whitelist_filters_pages PASSED
test_tag_pages_all_pages_outside_whitelist_returns_403 PASSED
test_tag_pages_no_whitelist_entries_returns_403 PASSED
```

---

## 📊 Режимна матриця

| Режим         | dry_run=true | dry_run=false | Whitelist |
|---------------|--------------|---------------|-----------|
| **TEST**      | Симуляція    | Симуляція (forced) | ✅ Так |
| **SAFE_TEST** | Симуляція    | Реальні зміни | ✅ Так |
| **PROD**      | Симуляція    | Реальні зміни | ✅ Так |

---

## 📚 Додаткова документація

- [TAG_PAGES_ENDPOINT.md](TAG_PAGES_ENDPOINT.md) — повна API документація
- [TAG_PAGES_WHITELIST.md](TAG_PAGES_WHITELIST.md) — технічна документація whitelist
- [WHITELIST_MECHANISM.md](WHITELIST_MECHANISM.md) — загальна документація whitelist

---

## ✅ Чеклист перед продакшн

- [ ] Whitelist налаштований у `whitelist_config.json`
- [ ] Тестовий dry-run виконаний успішно
- [ ] Режим `TAGGING_AGENT_MODE` встановлений правильно
- [ ] Confluence credentials налаштовані
- [ ] Тести проходять (`pytest tests/test_tag_pages_modes.py`)
- [ ] Логування моніториться

---

**Версія:** 2.1  
**Останнє оновлення:** 2025-12-29
