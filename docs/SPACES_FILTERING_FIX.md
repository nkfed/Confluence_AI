# Spaces Filtering Fix - Exclude Instead of Include

## Проблема

Реалізація фільтрації у GET /spaces мала помилку: замість **виключення** просторів за типом/статусом — реалізовано **включення**.

## Виправлення

### ✅ 1. Оновлено API /spaces

**Файл:** [src/api/routers/spaces.py](../src/api/routers/spaces.py)

**Зміни:**
- Параметри змінено з `Optional[str]` (comma-separated) на `List[str]` (масиви)
- Прибрано CSV парсинг
- Swagger тепер дозволяє додавати декілька значень через "Add item"

**Було:**
```python
exclude_types: Optional[str] = Query(
    default=None,
    description="Comma-separated list..."
)

# Парсинг
exclude_types_list = [t.strip() for t in exclude_types.split(",") if t.strip()]
```

**Стало:**
```python
exclude_types: List[str] = Query(
    default=[],
    description="List of space types to exclude..."
)

# Передається напряму
exclude_types=exclude_types if exclude_types else None
```

---

### ✅ 2. Підтверджено правильну логіку у SpaceService

**Файл:** [src/services/space_service.py](../src/services/space_service.py)

**Метод `filter_spaces()` вже мав правильну логіку виключення:**

```python
def filter_spaces(
    self,
    spaces: List[Dict[str, Any]],
    exclude_types: Optional[List[str]] = None,
    exclude_statuses: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    filtered = []
    
    for space in spaces:
        space_type = space.get("type", "")
        space_status = space.get("status", "")
        
        # OR логіка: виключити якщо type АБО status в exclude списках
        if space_type in exclude_types or space_status in exclude_statuses:
            excluded_count += 1
            continue  # ⭐ ВИКЛЮЧЕННЯ
        
        filtered.append(space)  # ⭐ ДОДАЄТЬСЯ ТІЛЬКИ ЯКЩ НЕ ВИКЛЮЧЕНО
    
    return filtered
```

**Логіка OR:** Простір виключається якщо `type ∈ exclude_types` **АБО** `status ∈ exclude_statuses`

---

### ✅ 3. Оновлено тести

**Файли:** 
- [tests/test_spaces_api.py](../tests/test_spaces_api.py) - додано `test_exclude_types_and_statuses_comprehensive()`
- [tests/test_spaces_meta.py](../tests/test_spaces_meta.py) - додано `test_filter_spaces_excludes_correctly()`

**Новий критичний тест:**
```python
def test_filter_spaces_excludes_correctly():
    """Перевіряє що filter_spaces ВИКЛЮЧАЄ, а не включає."""
    spaces = [
        {"id": "1", "key": "KEEP1", "type": "global", "status": "current"},
        {"id": "2", "key": "EXCLUDE_TYPE", "type": "personal", "status": "current"},
        {"id": "3", "key": "EXCLUDE_STATUS", "type": "global", "status": "archived"},
        {"id": "4", "key": "EXCLUDE_BOTH", "type": "personal", "status": "archived"}
    ]
    
    result = service.filter_spaces(
        spaces,
        exclude_types=["personal"],
        exclude_statuses=["archived"]
    )
    
    # Має залишитись тільки KEEP1
    assert len(result) == 1
    assert result[0]["key"] == "KEEP1"
    
    # Виключені НЕ присутні
    result_keys = [s["key"] for s in result]
    assert "EXCLUDE_TYPE" not in result_keys
    assert "EXCLUDE_STATUS" not in result_keys
    assert "EXCLUDE_BOTH" not in result_keys
```

---

## Тестування

### Результати тестів

```bash
.\.venv\Scripts\python.exe -m pytest tests/test_spaces_api.py tests/test_spaces_meta.py -v
```

```
✅ test_get_spaces_with_exclude_types - виключає типи
✅ test_get_spaces_with_exclude_statuses - виключає статуси
✅ test_get_spaces_with_both_filters - OR логіка
✅ test_get_spaces_with_multiple_exclude_types - декілька типів
✅ test_exclude_types_and_statuses_comprehensive - комплексний тест
✅ test_filter_spaces_excludes_correctly - критичний тест виключення

========== 23 passed, 0 failed ==========
```

---

## Приклади використання

### Swagger UI

У Swagger UI тепер можна додавати декілька значень через кнопку "Add item":

```
GET /spaces

Parameters:
  exclude_types: [Add item]
    - personal
    - team
  
  exclude_statuses: [Add item]
    - archived
```

### Curl

```bash
# Виключити personal простори
curl -X GET "http://localhost:8000/spaces?exclude_types=personal"

# Виключити archived статуси
curl -X GET "http://localhost:8000/spaces?exclude_statuses=archived"

# Виключити декілька типів
curl -X GET "http://localhost:8000/spaces?exclude_types=personal&exclude_types=team"

# OR логіка: виключити personal АБО archived
curl -X GET "http://localhost:8000/spaces?exclude_types=personal&exclude_statuses=archived"
```

### Python

```python
import httpx

# Виключити personal та archived
response = httpx.get(
    "http://localhost:8000/spaces",
    params={
        "exclude_types": ["personal", "team"],
        "exclude_statuses": ["archived"]
    }
)

spaces = response.json()["spaces"]

# Перевірка: виключені НЕ присутні
for space in spaces:
    assert space["type"] not in ["personal", "team"]
    assert space["status"] not in ["archived"]
```

---

## Критерії приймання

✅ `/spaces` виключає простори за типом/статусом (а не включає)  
✅ Логіка OR працює коректно  
✅ Параметри працюють як масиви (`List[str]`)  
✅ Swagger дозволяє додавати декілька значень  
✅ Всі 23 тести проходять  
✅ Немає включення замість виключення  
✅ Код типізований  
✅ Немає помилок  

---

## Таблиця фільтрації (OR логіка)

| Space | Type | Status | exclude_types=["personal"] | exclude_statuses=["archived"] | Виключений? | Причина |
|-------|------|--------|---------------------------|------------------------------|-------------|---------|
| S1 | global | current | ❌ | ❌ | ❌ НІ | Не відповідає жодній умові |
| S2 | personal | current | ✅ | ❌ | ✅ ТАК | type=personal |
| S3 | global | archived | ❌ | ✅ | ✅ ТАК | status=archived |
| S4 | personal | archived | ✅ | ✅ | ✅ ТАК | type=personal **АБО** status=archived |

**Висновок:** Простір виключається якщо хоча б одна умова виконується (OR).

---

## Файли змінені

1. ✅ [src/api/routers/spaces.py](../src/api/routers/spaces.py) - параметри на List[str]
2. ✅ [tests/test_spaces_api.py](../tests/test_spaces_api.py) - додано тест
3. ✅ [tests/test_spaces_meta.py](../tests/test_spaces_meta.py) - додано критичний тест

---

## Статистика

- **Файлів змінено:** 3
- **Нових тестів:** 2
- **Провалених тестів:** 0/23 ✅
- **Рядків змінено:** ~50

---

## Summary

Виправлено логіку фільтрації у GET /spaces:
- ✅ Параметри тепер масиви замість CSV
- ✅ Виключення працює правильно (не включення)
- ✅ OR логіка реалізована коректно
- ✅ Swagger підтримує декілька значень
- ✅ Всі тести проходять

**Система готова!** 🎉
