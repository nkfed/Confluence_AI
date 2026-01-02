# Централізований механізм ID-Whitelist для tag-space

## 🎯 Огляд

Централізований механізм керування whitelist для ендпоінта `POST /bulk/tag-space/{space_key}`.

**Ключові особливості:**
- Структурований по спейсах
- Root-сторінка необов'язкова (0 або 1)
- Whitelist-сторінки є точками входу
- Кожна точка входу обробляє своє піддерево
- У TEST/SAFE_TEST обробляються тільки whitelist-сторінки
- У PROD whitelist ігнорується
- Повністю відокремлений від `.env`

---

## 📁 Структура файлів

```
src/core/whitelist/
├── __init__.py
├── whitelist_manager.py       # WhitelistManager клас
└── whitelist_config.json      # Конфігурація whitelist
```

---

## 📋 Конфігурація whitelist

### Файл: `src/core/whitelist/whitelist_config.json`

```json
{
  "spaces": [
    {
      "space_key": "MYSPACE",
      "description": "Optional description",
      "pages": [
        {
          "id": 123456,
          "name": "Root documentation page",
          "root": true
        },
        {
          "id": 789012,
          "name": "Some subsection entry point",
          "root": false
        }
      ]
    }
  ]
}
```

### Правила:

1. **Root сторінка:**
   - Необов'язкова (може бути 0 або 1)
   - Якщо `root: true` → обробляється вся піддеревна структура
   - Дублювання root викликає warning при валідації

2. **Entry points (root: false):**
   - Можна додавати необмежену кількість
   - Кожен entry point обробляє свою сторінку + всі дочірні

3. **Дочірні сторінки:**
   - Автоматично успадковуються від entry points
   - Рекурсивно обходяться всі рівні вкладеності

---

## 🔧 WhitelistManager API

### Ініціалізація

```python
from src.core.whitelist import WhitelistManager

manager = WhitelistManager()  # Використовує default шлях
# або
manager = WhitelistManager("custom/path/to/config.json")
```

### Методи

#### `validate() -> List[str]`

Валідує конфігурацію:
- Не більше 1 root на space_key
- Всі ID є числами
- Структура валідна

```python
warnings = manager.validate()
if warnings:
    for warning in warnings:
        print(warning)
```

#### `get_entry_points(space_key: str) -> List[dict]`

Повертає список entry points для простору:

```python
entry_points = manager.get_entry_points("MYSPACE")
# [
#   {"id": 123456, "name": "Root", "root": true},
#   {"id": 789012, "name": "Entry", "root": false}
# ]
```

#### `get_allowed_ids(space_key: str, confluence_client) -> Set[int]`

Будує множину дозволених page_id:

```python
allowed_ids = await manager.get_allowed_ids("MYSPACE", confluence_client)
# {123456, 123457, 123458, 789012, 789013, ...}
```

**Кешування:** Результати кешуються для оптимізації.

#### `is_allowed(space_key: str, page_id: int, allowed_ids: Set[int]) -> bool`

Перевіряє чи дозволена сторінка:

```python
if manager.is_allowed("MYSPACE", 123456, allowed_ids):
    # Обробити сторінку
```

#### `clear_cache()`

Очищає кеш allowed_ids:

```python
manager.clear_cache()
```

---

## 🚀 Інтеграція у tag-space

### BulkTaggingService.tag_space()

```python
async def tag_space(self, space_key: str, dry_run: Optional[bool] = None):
    # 1. Визначення режиму
    mode = self.agent.mode  # TEST, SAFE_TEST, або PROD
    
    # 2. Ініціалізація WhitelistManager
    whitelist_manager = WhitelistManager()
    
    # 3. Визначення чи застосовувати whitelist
    whitelist_enabled = mode in ["TEST", "SAFE_TEST"]
    
    # 4. Завантаження allowed_ids
    if whitelist_enabled:
        allowed_ids = await whitelist_manager.get_allowed_ids(space_key, self.confluence)
    
    # 5. Фільтрація сторінок
    for page_id in all_pages:
        if whitelist_enabled:
            if not whitelist_manager.is_allowed(space_key, page_id, allowed_ids):
                # Пропустити сторінку
                continue
        
        # Обробити сторінку
        ...
```

---

## 📊 Режимна матриця

| Режим | Whitelist | Dry-run | Поведінка |
|-------|-----------|---------|-----------|
| **TEST** | ✅ Активний | ✅ Так | Тільки whitelist сторінки, без змін |
| **SAFE_TEST** | ✅ Активний | ❌ Ні | Тільки whitelist сторінки, реальні зміни |
| **PROD** | ❌ Ігнорується | ❌ Ні | Всі сторінки, реальні зміни |

---

## 🔍 Логування

Всі ключові події логуються:

```
[WhitelistManager] Loaded configuration from src/core/whitelist/whitelist_config.json
[WhitelistManager] Configuration validation passed
[WhitelistManager] Found 2 entry points for space MYSPACE
[WhitelistManager] Processing entry point: Root (id=123456, root=True)
[WhitelistManager] Added 15 children from 123456
[WhitelistManager] Total allowed_ids for MYSPACE: 25
[tag-space] Whitelist enabled: True
[tag-space] Whitelist loaded: 25 allowed pages for MYSPACE
[WhitelistManager] Page 999 is NOT in whitelist, skipping
[tag-space] After whitelist filter: 25 to process, 50 skipped
```

---

## ✅ Приклади використання

### 1. TEST режим з whitelist

```bash
curl -X POST "http://localhost:8000/bulk/tag-space/MYSPACE"
```

**Результат:**
```json
{
  "mode": "TEST",
  "whitelist_enabled": true,
  "dry_run": true,
  "total": 75,
  "processed": 25,
  "skipped_by_whitelist": 50,
  "success": 25
}
```

### 2. PROD режим без whitelist

```bash
curl -X POST "http://localhost:8000/bulk/tag-space/MYSPACE"
```

**Результат:**
```json
{
  "mode": "PROD",
  "whitelist_enabled": false,
  "dry_run": false,
  "total": 75,
  "processed": 75,
  "skipped_by_whitelist": 0,
  "success": 75
}
```

---

## 🧪 Тестування

```bash
# Тести WhitelistManager
pytest tests/test_whitelist_manager.py -v

# Інтеграційні тести tag_space
pytest tests/test_tag_space_whitelist_integration.py -v
```

---

## ⚠️ Важливі зауваження

1. **Тільки для tag-space:** Інші ендпоінти (tag-tree, auto-tag, tag-pages) не використовують цей механізм.

2. **Без .env:** Whitelist повністю керується через `whitelist_config.json`, незалежно від `.env`.

3. **Root необов'язковий:** Можна мати тільки entry points без root.

4. **Дублікати root:** Якщо є >1 root на space_key, валідація поверне warning (але не зламає роботу).

5. **Кешування:** Результати `get_allowed_ids()` кешуються. Для оновлення викликайте `clear_cache()`.

6. **Рекурсія:** Дочірні сторінки обходяться рекурсивно до найглибшого рівня.

---

## 🔄 Міграція з старого whitelist

**Старий підхід (.env):**
```env
ALLOWED_TAGGING_PAGES=19713687690,19699862097
```

**Новий підхід (whitelist_config.json):**
```json
{
  "spaces": [
    {
      "space_key": "~62e7af26f15eecaf500d44bc",
      "pages": [
        {"id": 19713687690, "name": "Test Page 1", "root": true},
        {"id": 19699862097, "name": "Test Page 2", "root": false}
      ]
    }
  ]
}
```

**Переваги:**
- Структурований по спейсах
- Підтримка піддерев
- Незалежність від .env
- Валідація та логування
- Легке розширення

---

## 📞 Додаткова інформація

- **Код:** `src/core/whitelist/whitelist_manager.py`
- **Конфігурація:** `src/core/whitelist/whitelist_config.json`
- **Тести:** `tests/test_whitelist_manager.py`
- **Інтеграція:** `src/services/bulk_tagging_service.py::tag_space()`
