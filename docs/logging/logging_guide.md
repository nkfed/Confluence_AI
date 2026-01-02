# Розширена система логування - Документація

## Огляд

Модуль `src/utils/log.py` надає розширений функціонал для логування з підтримкою аудиту, JSON-логів, метрик та генерації SQL.

## Доступні функції

### 1. `log.info(message, *args, **kwargs)`
Записує INFO-повідомлення в `logs/utils.log`.

**Параметри:**
- `message` (str): Повідомлення для логування
- `*args`: Додаткові аргументи для форматування
- `**kwargs`: Додаткові параметри для logger.info()

**Приклад:**
```python
from src.utils import log

log.info("Processing page %s", page_id)
log.info("Started bulk tagging operation")
```

---

### 2. `log.error(message, *args, **kwargs)`
Записує ERROR-повідомлення в `logs/utils.log`.

**Приклад:**
```python
log.error("Failed to process page %s: %s", page_id, error)
log.error("Connection timeout after 3 retries")
```

---

### 3. `log.warning(message, *args, **kwargs)`
Записує WARNING-повідомлення в `logs/utils.log`.

**Приклад:**
```python
log.warning("Page %s not found in whitelist", page_id)
log.warning("Deprecated API endpoint used")
```

---

### 4. `log.debug(message, *args, **kwargs)`
Записує DEBUG-повідомлення в `logs/utils.log`.

**Приклад:**
```python
log.debug("Extracted %d characters from page", len(text))
log.debug("Cache hit for key: %s", cache_key)
```

---

### 5. `log.critical(message, *args, **kwargs)`
Записує CRITICAL-повідомлення в `logs/utils.log`.

**Приклад:**
```python
log.critical("System failure: %s", error)
log.critical("Database connection lost")
```

---

### 6. `log.audit(message, actor=None, action=None)` ✨ НОВА

Записує AUDIT-повідомлення про дії користувача або агента.

**Параметри:**
- `message` (str): Основне повідомлення аудиту
- `actor` (Optional[str]): Ім'я користувача/агента, що виконав дію
- `action` (Optional[str]): Тип дії

**Формат виводу:**
```
[AUDIT] [actor] [action] message
```

**Приклади:**
```python
# З actor та action
log.audit("Tagged 5 pages", actor="BulkTaggingService", action="tag_pages")
# Вивід: [AUDIT] [BulkTaggingService] [tag_pages] Tagged 5 pages

# Тільки з actor
log.audit("User logged in", actor="john@example.com")
# Вивід: [AUDIT] [john@example.com] User logged in

# Без параметрів
log.audit("System started")
# Вивід: [AUDIT] [system] System started
```

---

### 7. `log.log_json(data, level="INFO")` ✨ НОВА

Серіалізує словник у JSON та записує в `logs/utils.log`.

**Параметри:**
- `data` (dict): Словник з даними для логування
- `level` (str): Рівень логування (INFO, ERROR, WARNING, DEBUG)

**Приклади:**
```python
# Базовий JSON
log.log_json({
    "page_id": "123",
    "tags": ["tag1", "tag2"],
    "status": "success"
})

# JSON з рівнем ERROR
log.log_json({
    "error": "Connection failed",
    "code": 500,
    "retry_count": 3
}, level="ERROR")

# Складний об'єкт
log.log_json({
    "service": "BulkTaggingService",
    "operation": "tag_pages",
    "stats": {
        "total": 100,
        "success": 95,
        "errors": 5
    }
})
```

---

### 8. `log.log_to_db(data, table="logs")` ✨ НОВА

Генерує SQL-запит INSERT для збереження логів у базу даних (SQLite/PostgreSQL).  
**Увага:** Функція НЕ виконує запит, тільки повертає SQL рядок.

**Параметри:**
- `data` (dict): Словник з даними для збереження
- `table` (str): Назва таблиці (за замовчуванням "logs")

**Повертає:**
- `str`: SQL-запит INSERT

**Приклади:**
```python
# Генерація SQL для таблиці logs
sql = log.log_to_db({
    "level": "INFO",
    "message": "Page processed",
    "page_id": "123456"
})
# Повертає: INSERT INTO logs (timestamp, level, message, page_id) VALUES ('2025-12-26 12:00:00', 'INFO', 'Page processed', '123456');

# Генерація SQL для кастомної таблиці
sql = log.log_to_db({
    "action": "tag_pages",
    "actor": "BulkTaggingService",
    "success_count": 10
}, table="audit_logs")

# Використання SQL (приклад з SQLite)
import sqlite3
conn = sqlite3.connect("app.db")
cursor = conn.cursor()
cursor.execute(sql)
conn.commit()
```

**Примітка:** Timestamp додається автоматично, якщо не вказаний у `data`.

---

### 9. `log.log_metrics(name, value, tags=None)` ✨ НОВА

Записує метрику в `logs/utils.log` у структурованому форматі.

**Параметри:**
- `name` (str): Назва метрики
- `value` (Union[int, float]): Значення метрики (число)
- `tags` (Optional[dict]): Додаткові теги для класифікації метрики

**Формат виводу:**
```
[METRIC] name=value tags={"key": "value"}
```

**Приклади:**
```python
# Проста метрика
log.log_metrics("pages_tagged", 42)
# Вивід: [METRIC] pages_tagged=42

# Метрика з тегами
log.log_metrics("api_response_time", 0.523, tags={
    "endpoint": "/bulk/tag-pages",
    "status": "success"
})
# Вивід: [METRIC] api_response_time=0.523 tags={"endpoint": "/bulk/tag-pages", "status": "success"}

# Метрика помилок
log.log_metrics("error_count", 3, tags={
    "service": "BulkTaggingService",
    "error_type": "timeout"
})
```

**Використання для моніторингу:**
```python
import time

start_time = time.time()
# ... виконання операції ...
elapsed_time = time.time() - start_time

log.log_metrics("operation_duration", elapsed_time, tags={
    "operation": "bulk_tagging",
    "pages": 100
})
```

---

### 10. `log.log_rotation()` ✨ НОВА

Повертає інформацію про налаштування ротації логів.

**Повертає:**
- `dict`: Інформація про налаштування ротації

**Приклад:**
```python
info = log.log_rotation()
print(info)
# {
#     'max_bytes': 5242880,      # 5MB
#     'backup_count': 3,
#     'encoding': 'utf-8',
#     'configured': True,
#     'note': 'RotatingFileHandler налаштований у src/core/logging/logging_config.py'
# }
```

**Налаштування RotatingFileHandler:**
- Максимальний розмір файлу: **5MB**
- Кількість бекапів: **3**
- Кодування: **UTF-8**
- Автоматична ротація при досягненні ліміту

**Файли після ротації:**
```
logs/utils.log      # Поточний файл
logs/utils.log.1    # Перший бекап
logs/utils.log.2    # Другий бекап
logs/utils.log.3    # Третій бекап (найстаріший)
```

---

## Комплексний приклад використання

```python
from src.utils import log

# 1. Початок операції
log.audit("Starting bulk tagging", actor="BulkTaggingService", action="tag_pages")
log.info("Processing 100 pages")

# 2. Обробка сторінок
for page_id in page_ids:
    try:
        # Логування деталей
        log.debug(f"Processing page {page_id}")
        
        # Виклик AI та тегування
        tags = generate_tags(page_id)
        
        # JSON-лог успішної операції
        log.log_json({
            "page_id": page_id,
            "status": "success",
            "tags": tags
        })
        
        # Метрика успіху
        log.log_metrics("page_tagged", 1, tags={
            "page_id": page_id,
            "status": "success"
        })
        
    except Exception as e:
        # Логування помилки
        log.error(f"Failed to process page {page_id}: {e}")
        
        # JSON-лог помилки
        log.log_json({
            "page_id": page_id,
            "status": "error",
            "error": str(e)
        }, level="ERROR")
        
        # Метрика помилки
        log.log_metrics("page_error", 1, tags={
            "page_id": page_id,
            "error_type": type(e).__name__
        })

# 3. Завершення операції
log.audit("Bulk tagging completed", actor="BulkTaggingService", action="tag_pages")
log.log_metrics("total_pages_processed", len(page_ids))

# 4. Збереження аудиту в БД (опціонально)
sql = log.log_to_db({
    "action": "tag_pages",
    "actor": "BulkTaggingService",
    "pages_count": len(page_ids),
    "success": True
}, table="audit_logs")
# Виконати SQL у БД...
```

---

## Формати логів у logs/utils.log

```
2025-12-26 12:00:00 | INFO | utils | None | Processing 100 pages
2025-12-26 12:00:01 | INFO | utils | None | [AUDIT] [BulkTaggingService] [tag_pages] Starting bulk tagging
2025-12-26 12:00:02 | DEBUG | utils | None | Processing page 123
2025-12-26 12:00:03 | INFO | utils | None | JSON: {"page_id": "123", "status": "success", "tags": ["doc-tech"]}
2025-12-26 12:00:04 | INFO | utils | None | [METRIC] page_tagged=1 tags={"page_id": "123", "status": "success"}
2025-12-26 12:00:05 | ERROR | utils | None | Failed to process page 456: Connection timeout
2025-12-26 12:00:06 | INFO | utils | None | [METRIC] total_pages_processed=100
```

---

## Переваги нової системи

✅ **Аудит дій** — відстеження всіх важливих операцій з actor/action  
✅ **JSON-логування** — структуровані дані для парсингу та аналізу  
✅ **Метрики** — вбудований моніторинг продуктивності  
✅ **SQL-генерація** — готовність до логування в БД  
✅ **Автоматична ротація** — захист від переповнення диска  
✅ **Уніфікований формат** — легко парсити та аналізувати  

---

## Тестування

Запусти файл з прикладами:
```bash
python examples_logging.py
```

Перевір результат:
```bash
cat logs/utils.log
# або
Get-Content logs/utils.log -Tail 50
```
