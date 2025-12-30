# 🔍 Діагностичний аналіз: Чому whitelist не працює в tag-space

**Дата:** 2025-12-29  
**Аналізовано:** `src/services/bulk_tagging_service.py`, `src/core/bulk_tag_orchestrator.py`, `src/api/routers/bulk_tag_space.py`

---

## 🎯 Висновок: КРИТИЧНА ПРОБЛЕМА ВИЯВЛЕНА

**Причина:** **Роутер викликає НЕПРАВИЛЬНИЙ метод!**

Роутер `bulk_tag_space.py` викликає:
```python
orchestrator = BulkTagOrchestrator()
result = await orchestrator.tag_space(...)  # ← НЕПРАВИЛЬНИЙ МЕТОД
```

А має викликати:
```python
service = BulkTaggingService()
result = await service.tag_space(...)  # ← ПРАВИЛЬНИЙ МЕТОД
```

---

## 📊 Карта виконання

### 1️⃣ Правильний шлях (з whitelist) — НЕ ВИКОРИСТОВУЄТЬСЯ

```
bulk_tag_space.py (роутер)
    ❌ НЕ викликає
        ↓
BulkTaggingService.tag_space()
    ✅ Завантажує whitelist
    ✅ Фільтрує page_ids через allowed_ids
    ✅ Викликає tag_pages() з відфільтрованими ID
        ↓
BulkTaggingService.tag_pages()
    ✅ Отримує вже відфільтровані page_ids
    ✅ Обробляє тільки whitelist сторінки
```

### 2️⃣ Поточний шлях (БЕЗ whitelist) — ВИКОРИСТОВУЄТЬСЯ

```
bulk_tag_space.py (роутер)
    ❌ ВИКЛИКАЄ НЕПРАВИЛЬНИЙ КЛАС
        ↓
BulkTagOrchestrator.tag_space()  ← ЗАСТАРІЛИЙ КЛАС
    ❌ Використовує старий whitelist механізм
    ❌ НЕ використовує WhitelistManager
    ❌ Викликає self.filter_service.should_exclude_page()
    ❌ Старий whitelist з AgentModeResolver
        ↓
PageFilterService.should_exclude_page()
    ❌ Перевіряє whitelist старим способом
    ❌ У PROD режимі whitelist ігнорується
```

---

## 🔴 ПРОБЛЕМА #1: Роутер викликає неправильний клас

### Поточний код:
**Файл:** `src/api/routers/bulk_tag_space.py`

```python
@router.post("/tag-space/{space_key}")
async def bulk_tag_space(...):
    orchestrator = BulkTagOrchestrator()  # ← НЕПРАВИЛЬНО
    result = await orchestrator.tag_space(...)
```

### Що відбувається:
- Роутер створює екземпляр **BulkTagOrchestrator**
- BulkTagOrchestrator — це **ЗАСТАРІЛИЙ** клас
- Він використовує **старий whitelist механізм**
- У PROD режимі він **ігнорує whitelist**

---

## 🔴 ПРОБЛЕМА #2: Два різних методи tag_space()

### ✅ Правильний метод (з новим whitelist):

**Файл:** `src/services/bulk_tagging_service.py`  
**Клас:** `BulkTaggingService`  
**Метод:** `tag_space()`

```python
async def tag_space(self, space_key: str, dry_run: Optional[bool] = None) -> dict:
    # ✅ Завантажує whitelist через WhitelistManager
    whitelist_manager = WhitelistManager()
    allowed_ids = await whitelist_manager.get_allowed_ids(space_key, self.confluence)
    
    # ✅ Отримує всі сторінки простору
    page_ids = await self.confluence.get_all_pages_in_space(space_key)
    
    # ✅ Фільтрує через whitelist
    for page_id in page_ids:
        if whitelist_manager.is_allowed(space_key, page_id_int, allowed_ids):
            pages_to_process.append(page_id)
    
    # ✅ Викликає tag_pages() з відфільтрованими ID
    result = await self.tag_pages(pages_to_process, space_key, dry_run, task_id)
```

**Характеристики:**
- ✅ Використовує **WhitelistManager**
- ✅ Використовує **whitelist_config.json**
- ✅ Завжди застосовує whitelist
- ✅ Працює в усіх режимах (TEST, SAFE_TEST, PROD)
- ✅ Уніфікована dry_run матриця
- ✅ Підтримує зупинку процесу (task_id)

---

### ❌ Неправильний метод (зі старим whitelist):

**Файл:** `src/core/bulk_tag_orchestrator.py`  
**Клас:** `BulkTagOrchestrator`  
**Метод:** `tag_space()`

```python
async def tag_space(self, space_key: str, dry_run_override: Optional[bool] = None, ...) -> Dict[str, Any]:
    # ❌ Використовує старий whitelist
    self.mode = AgentModeResolver.resolve_mode(self.AGENT_NAME)
    self.whitelist = AgentModeResolver.resolve_whitelist(self.AGENT_NAME)
    
    # ❌ Отримує всі сторінки (з повною інформацією)
    pages = await self.confluence.get_pages_in_space(space_key, expand="body.storage,version")
    
    # ❌ Фільтрує через старий механізм
    filtered_pages, skipped_pages = self._filter_pages(pages, ...)
    
    # ❌ Обробляє сторінки напряму (НЕ через tag_pages)
    for page in filtered_pages:
        result = await self._tag_page(page, dry_run)
```

**Характеристики:**
- ❌ Використовує **AgentModeResolver** (застарілий)
- ❌ Використовує **змінні оточення** (ALLOWED_TAGGING_PAGES)
- ❌ НЕ використовує **WhitelistManager**
- ❌ НЕ використовує **whitelist_config.json**
- ❌ У PROD режимі **ігнорує whitelist**
- ❌ Має інші параметри (exclude_archived, exclude_index_pages, ...)
- ❌ НЕ підтримує зупинку процесу

---

## 🔍 Детальний аналіз BulkTagOrchestrator

### Проблемні місця:

#### 1. Ініціалізація з старим whitelist:

```python
def __init__(self, ...):
    self.mode = AgentModeResolver.resolve_mode(self.AGENT_NAME)
    self.whitelist = AgentModeResolver.resolve_whitelist(self.AGENT_NAME)
    self.filter_service = PageFilterService(whitelist=self.whitelist)
```

**Проблема:** 
- `AgentModeResolver.resolve_whitelist()` повертає список з **ALLOWED_TAGGING_PAGES**
- Ці змінні **видалені** з `.env` та `settings.py`
- Whitelist завжди **порожній** або **не працює**

#### 2. Фільтрація через PageFilterService:

```python
def _filter_pages(self, pages, ...):
    for page in pages:
        should_exclude, reason = self.filter_service.should_exclude_page(
            page=page,
            mode=self.mode,
            exclude_archived=exclude_archived,
            ...
        )
```

**Проблема:**
- PageFilterService використовує **старий whitelist**
- У PROD режимі whitelist **не застосовується**
- Фільтрація відбувається за **іншими критеріями** (archived, index, templates)

#### 3. Обробка кожної сторінки окремо:

```python
for page in filtered_pages:
    result = await self._tag_page(page, dry_run)
    details.append(result)
```

**Проблема:**
- НЕ викликає `tag_pages()` з BulkTaggingService
- Обробляє сторінки **напряму**
- НЕ використовує уніфіковану логіку

---

## 🔍 Аналіз confluence_client.py

### Методи для отримання сторінок:

#### 1. `get_all_pages_in_space(space_key)` → list[str]
- Повертає **список ID** сторінок
- Викликається в **BulkTaggingService.tag_space()**
- ✅ Правильно використовується

#### 2. `get_pages_in_space(space_key, expand)` → list[Dict]
- Повертає **повні об'єкти** сторінок
- Викликається в **BulkTagOrchestrator.tag_space()**
- ❌ Неправильно використовується (застарілий метод)

---

## 🔍 Аналіз роутера bulk_tag_space.py

### Поточний код:

```python
@router.post("/tag-space/{space_key}")
async def bulk_tag_space(space_key: str, dry_run: Optional[bool] = None, ...):
    orchestrator = BulkTagOrchestrator()  # ← ПОМИЛКА ТУТ
    result = await orchestrator.tag_space(
        space_key=space_key,
        dry_run_override=dry_run,
        exclude_archived=exclude_archived,
        ...
    )
    return result
```

### Що не так:

1. **Викликає неправильний клас:** `BulkTagOrchestrator` замість `BulkTaggingService`
2. **Використовує застарілий API:** `dry_run_override`, `exclude_archived`, ...
3. **Не отримує task_id у відповіді**
4. **Whitelist не працює через старий механізм**

---

## 📝 Діагностична карта виконання

### Поточне виконання tag-space (НЕПРАВИЛЬНЕ):

```
HTTP POST /bulk/tag-space/SPACE_KEY
    ↓
bulk_tag_space.py::bulk_tag_space()
    ↓
    orchestrator = BulkTagOrchestrator()  ← ЗАСТАРІЛИЙ КЛАС
    ↓
BulkTagOrchestrator.__init__()
    ├── self.mode = AgentModeResolver.resolve_mode()
    ├── self.whitelist = AgentModeResolver.resolve_whitelist()  ← СТАРИЙ МЕХАНІЗМ
    └── self.filter_service = PageFilterService(whitelist=self.whitelist)
    ↓
BulkTagOrchestrator.tag_space()
    ├── pages = await self.confluence.get_pages_in_space()  ← ВСІ СТОРІНКИ
    ├── filtered_pages = self._filter_pages(pages)  ← ФІЛЬТРАЦІЯ БЕЗ WHITELIST
    │   └── PageFilterService.should_exclude_page()
    │       ├── Перевірка: archived, index, templates, empty
    │       └── У PROD: whitelist НЕ застосовується
    ↓
    for page in filtered_pages:  ← ОБРОБКА ВСЮ СТОРІНОК
        await self._tag_page(page, dry_run)
```

### Правильне виконання tag-space (ПОТРІБНЕ):

```
HTTP POST /bulk/tag-space/SPACE_KEY
    ↓
bulk_tag_space.py::bulk_tag_space()
    ↓
    service = BulkTaggingService()  ← ПРАВИЛЬНИЙ КЛАС
    ↓
BulkTaggingService.tag_space()
    ├── whitelist_manager = WhitelistManager()  ← НОВИЙ МЕХАНІЗМ
    ├── allowed_ids = await whitelist_manager.get_allowed_ids()
    ├── page_ids = await self.confluence.get_all_pages_in_space()
    ├── Фільтрація:
    │   for page_id in page_ids:
    │       if page_id in allowed_ids:  ← WHITELIST ЗАСТОСОВУЄТЬСЯ
    │           pages_to_process.append(page_id)
    ↓
    result = await self.tag_pages(pages_to_process, ...)  ← ТІЛЬКИ WHITELIST
```

---

## 🔴 Список критичних проблем

### 1. **Роутер викликає неправильний клас**
- **Файл:** `src/api/routers/bulk_tag_space.py`
- **Рядок:** ~170
- **Проблема:** Викликає `BulkTagOrchestrator` замість `BulkTaggingService`
- **Наслідок:** Whitelist не працює взагалі

### 2. **BulkTagOrchestrator використовує старий whitelist**
- **Файл:** `src/core/bulk_tag_orchestrator.py`
- **Рядок:** ~51
- **Проблема:** `AgentModeResolver.resolve_whitelist()` повертає порожній список
- **Наслідок:** Whitelist завжди порожній

### 3. **Змінні ALLOWED_TAGGING_PAGES видалені**
- **Файл:** `.env`, `settings.py`
- **Проблема:** Змінні видалені, але `AgentModeResolver` їх шукає
- **Наслідок:** Whitelist завжди порожній

### 4. **У PROD режимі whitelist ігнорується**
- **Файл:** `src/services/page_filter_service.py` (припущення)
- **Проблема:** PageFilterService не застосовує whitelist у PROD
- **Наслідок:** У PROD обробляються ВСІ сторінки

### 5. **Різні сигнатури методів**
- `BulkTaggingService.tag_space(space_key, dry_run)`
- `BulkTagOrchestrator.tag_space(space_key, dry_run_override, exclude_*)`
- **Наслідок:** Роутер передає параметри, які не використовуються

---

## ✅ Рішення

### Крок 1: Виправити роутер

**Файл:** `src/api/routers/bulk_tag_space.py`

**Було:**
```python
orchestrator = BulkTagOrchestrator()
result = await orchestrator.tag_space(...)
```

**Має бути:**
```python
from src.services.bulk_tagging_service import BulkTaggingService

service = BulkTaggingService()
result = await service.tag_space(
    space_key=space_key,
    dry_run=dry_run
)
```

### Крок 2: Видалити параметри exclude_*

Ці параметри були для BulkTagOrchestrator, але BulkTaggingService їх не використовує:
- `exclude_archived`
- `exclude_index_pages`
- `exclude_templates`
- `exclude_empty_pages`
- `exclude_by_title_regex`

### Крок 3: Оновити документацію роутера

Документація описує логіку BulkTagOrchestrator, але має описувати BulkTaggingService.

### Крок 4 (опціонально): Перемістити BulkTagOrchestrator в deprecated

Якщо він більше не використовується.

---

## 📊 Порівняльна таблиця

| Аспект | BulkTaggingService | BulkTagOrchestrator |
|--------|-------------------|---------------------|
| **Whitelist механізм** | ✅ WhitelistManager + whitelist_config.json | ❌ AgentModeResolver + env vars |
| **Застосування whitelist** | ✅ Завжди (TEST, SAFE_TEST, PROD) | ❌ Тільки TEST/SAFE_TEST |
| **Джерело whitelist** | ✅ whitelist_config.json | ❌ ALLOWED_TAGGING_PAGES (видалено) |
| **Dry-run матриця** | ✅ Уніфікована | ❌ Стара логіка |
| **Підтримка task_id** | ✅ Так (зупинка процесу) | ❌ Ні |
| **Сигнатура методу** | `tag_space(space_key, dry_run)` | `tag_space(space_key, dry_run_override, exclude_*)` |
| **Фільтрація сторінок** | ✅ Через whitelist | ❌ Через exclude_* параметри |
| **Виклик tag_pages()** | ✅ Так | ❌ Ні (обробка напряму) |
| **Актуальність** | ✅ Актуальний | ❌ Застарілий |

---

## 🎯 Фінальний висновок

### Причина проблеми:

**Роутер викликає НЕПРАВИЛЬНИЙ клас.**

Роутер `bulk_tag_space.py` викликає застарілий `BulkTagOrchestrator`, який:
1. Використовує старий whitelist механізм (AgentModeResolver)
2. Шукає змінні оточення, які були видалені
3. У PROD режимі ігнорує whitelist
4. НЕ використовує WhitelistManager
5. НЕ використовує whitelist_config.json

### Рішення:

**Змінити роутер на виклик правильного класу:**

```python
# Було
orchestrator = BulkTagOrchestrator()
result = await orchestrator.tag_space(...)

# Має бути
service = BulkTaggingService()
result = await service.tag_space(space_key=space_key, dry_run=dry_run)
```

### Після виправлення:

✅ Whitelist буде працювати  
✅ Усі режими (TEST, SAFE_TEST, PROD) будуть використовувати whitelist  
✅ Whitelist буде завантажуватися з whitelist_config.json  
✅ Буде підтримуватися зупинка процесу (task_id)  
✅ Уніфікована логіка з tag-pages і tag-tree  

---

**Звіт створено:** 2025-12-29  
**Аналізовано:** 3 файли  
**Критичних проблем:** 5  
**Рішення:** 1 (змінити роутер)
