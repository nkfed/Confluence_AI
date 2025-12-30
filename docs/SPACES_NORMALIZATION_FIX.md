# Normalization Fix for Spaces Filtering

## Проблема

Swagger передавав параметри фільтрації у некоректному форматі:
- Замість `personal` приходило `['personal']` або `"personal"`
- Це ламало фільтрацію, бо `filter_spaces()` шукав точне співпадіння значень

## Рішення

### ✅ 1. Додано функцію нормалізації

**Файл:** [src/api/routers/spaces.py](../src/api/routers/spaces.py)

```python
def normalize_list_param(values: List[str]) -> List[str]:
    """
    Нормалізує параметри списку, видаляючи лапки, дужки та зайві пробіли.
    """
    normalized = []
    for v in values:
        # Видалити дужки, лапки та пробіли
        v = v.strip("[]'\" ")
        if v:
            normalized.append(v)
    return normalized
```

**Що робить:**
- Видаляє `[]` (дужки)
- Видаляє `'` та `"` (лапки)
- Видаляє зайві пробіли
- Фільтрує порожні значення

---

### ✅ 2. Застосовано нормалізацію в роутері

```python
@router.get("/spaces")
async def get_spaces(...):
    # Нормалізувати параметри
    exclude_types = normalize_list_param(exclude_types) if exclude_types else []
    exclude_statuses = normalize_list_param(exclude_statuses) if exclude_statuses else []
    
    logger.info(f"Normalized filters: exclude_types={exclude_types}, exclude_statuses={exclude_statuses}")
```

**Логування показує:**
```
GET /spaces: exclude_types=['personal'], exclude_statuses=['archived']
Normalized filters: exclude_types=['personal'], exclude_statuses=['archived']
```

---

### ✅ 3. Оновлено Swagger описи

**Було:**
```python
description="List of space types to exclude (e.g., ['personal', 'global'])"
```

**Стало:**
```python
description="List of space types to exclude. Example: personal, global (enter each as separate item)"
```

Тепер користувач розуміє що вводити **без** дужок та лапок.

---

### ✅ 4. Додано тести

**Файл:** [tests/test_normalize_filters.py](../tests/test_normalize_filters.py) - 8 тестів

**Тест нормалізації:**
```python
def test_normalize_list_param_with_brackets():
    input_values = ["['personal']", "['global']"]
    result = normalize_list_param(input_values)
    assert result == ["personal", "global"]  # ✅ Дужки та лапки видалені
```

**Файл:** [tests/test_spaces_api.py](../tests/test_spaces_api.py) - +1 новий тест

**Тест реальної фільтрації:**
```python
@pytest.mark.asyncio
async def test_exclude_personal_and_archived_spaces():
    """Перевіряє що фільтрація реально виключає простори."""
    result = await service.get_spaces(
        exclude_types=["personal"],
        exclude_statuses=["archived"]
    )
    
    # Verify виключені НЕ присутні
    for space in result["spaces"]:
        assert space["type"] != "personal"
        assert space["status"] != "archived"
```

---

## Тестування

### Результати тестів

```bash
.\.venv\Scripts\python.exe -m pytest tests/test_normalize_filters.py tests/test_spaces_api.py -v
```

```
✅ test_normalize_list_param_with_brackets - дужки видаляються
✅ test_normalize_list_param_with_quotes - лапки видаляються
✅ test_normalize_list_param_clean - чисті значення
✅ test_normalize_list_param_with_spaces - пробіли видаляються
✅ test_normalize_list_param_empty - порожній список
✅ test_normalize_list_param_with_empty_strings - порожні рядки
✅ test_normalize_list_param_complex - складні випадки
✅ test_normalize_list_param_real_swagger_format - реальний Swagger
✅ test_exclude_personal_and_archived_spaces - реальна фільтрація

========== 20 passed, 0 failed ==========
```

---

## Демонстрація роботи

### Вхідні формати та результати

| Вхідні дані Swagger | Нормалізовано | Статус |
|---------------------|---------------|--------|
| `['personal']` | `personal` | ✅ |
| `"personal"` | `personal` | ✅ |
| `'personal'` | `personal` | ✅ |
| ` personal ` | `personal` | ✅ |
| `["['personal']"]` | `personal` | ✅ |
| `["", "personal"]` | `["personal"]` | ✅ |

---

## Приклади використання

### Swagger UI

**До виправлення:**
```
exclude_types: ['personal']  ❌ НЕ ПРАЦЮВАЛО
```

**Після виправлення:**
```
exclude_types: personal      ✅ ПРАЦЮЄ
або
exclude_types: ['personal']  ✅ ТАКОЖ ПРАЦЮЄ (нормалізується)
```

### Curl

```bash
# Виключити personal простори
curl "http://localhost:8000/spaces?exclude_types=personal"

# Виключити archived
curl "http://localhost:8000/spaces?exclude_statuses=archived"

# Виключити декілька типів
curl "http://localhost:8000/spaces?exclude_types=personal&exclude_types=collaboration"
```

### Python

```python
response = httpx.get(
    "http://localhost:8000/spaces",
    params={
        "exclude_types": ["personal", "global"],
        "exclude_statuses": ["archived"]
    }
)

# Перевірка - виключені НЕ присутні
for space in response.json()["spaces"]:
    assert space["type"] not in ["personal", "global"]
    assert space["status"] != "archived"
```

---

## Критерії приймання

✅ `exclude_types` та `exclude_statuses` нормалізуються  
✅ Фільтрація працює навіть якщо значення містять лапки або дужки  
✅ Swagger-опис не вводить в оману  
✅ Тест `test_exclude_personal_and_archived_spaces` проходить  
✅ Логування показує `Filtered spaces: kept X, excluded Y`  
✅ Всі 20 тестів проходять  

---

## Логування

### До виправлення

```
GET /spaces: exclude_types=['personal'], exclude_statuses=['archived']
Filtered spaces: kept 5, excluded 0  ❌ Фільтрація не спрацювала
```

### Після виправлення

```
GET /spaces: exclude_types=['personal'], exclude_statuses=['archived']
Normalized filters: exclude_types=['personal'], exclude_statuses=['archived']
Excluding space PERSONAL_CURRENT: type=personal, status=current
Excluding space GLOBAL_ARCHIVED: type=global, status=archived
Excluding space PERSONAL_ARCHIVED: type=personal, status=archived
Filtered spaces: kept 2, excluded 3  ✅ Фільтрація спрацювала
```

---

## Файли змінені

1. ✅ [src/api/routers/spaces.py](../src/api/routers/spaces.py)
   - Додано `normalize_list_param()`
   - Застосовано нормалізацію перед викликом сервісу
   - Оновлено Swagger описи

2. ✅ [tests/test_normalize_filters.py](../tests/test_normalize_filters.py) (новий)
   - 8 тестів для нормалізації

3. ✅ [tests/test_spaces_api.py](../tests/test_spaces_api.py)
   - Додано `test_exclude_personal_and_archived_spaces()`

---

## Статистика

- **Файлів змінено:** 3 (2 оновлено, 1 новий)
- **Нових тестів:** 9
- **Провалених тестів:** 0/20 ✅
- **Рядків коду:** ~100

---

## Summary

Додано нормалізацію параметрів фільтрації у GET /spaces:
- ✅ Функція `normalize_list_param()` видаляє лапки, дужки, пробіли
- ✅ Застосовується автоматично перед фільтрацією
- ✅ Swagger тепер працює з будь-яким форматом
- ✅ Логування показує нормалізовані значення
- ✅ 20 тестів підтверджують коректність роботи

**Фільтрація тепер працює незалежно від формату параметрів!** 🎉
