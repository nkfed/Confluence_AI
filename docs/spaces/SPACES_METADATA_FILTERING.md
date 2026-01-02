# Spaces Metadata and Filtering - Implementation Guide

## Огляд

Додано новий функціонал для роботи з метаданими просторів Confluence та розширена фільтрація.

## Нові можливості

### 1. GET /spaces/meta - Метадані просторів

Повертає унікальні типи та статуси всіх просторів у Confluence.

**Ендпоінт:**
```
GET /spaces/meta
```

**Відповідь:**
```json
{
  "available_types": ["global", "personal", "team"],
  "available_statuses": ["current", "archived"]
}
```

**Використання:**
- Побудова UI фільтрів
- Валідація параметрів exclude_types та exclude_statuses
- Розуміння структури просторів

**Приклад:**
```bash
curl -X GET "http://localhost:8000/spaces/meta"
```

---

### 2. GET /spaces - Розширена фільтрація

Додано параметри для виключення просторів за типами та статусами.

**Нові параметри:**

| Параметр | Тип | Опис | Приклад |
|----------|-----|------|---------|
| `exclude_types` | string | Comma-separated типи для виключення | `personal,team` |
| `exclude_statuses` | string | Comma-separated статуси для виключення | `archived` |

**Логіка фільтрації (OR):**

Виключає простір якщо:
- `type ∈ exclude_types` **АБО**
- `status ∈ exclude_statuses`

**Приклади запитів:**

```bash
# Виключити personal простори
curl -X GET "http://localhost:8000/spaces?exclude_types=personal"

# Виключити archived простори
curl -X GET "http://localhost:8000/spaces?exclude_statuses=archived"

# Виключити personal АБО archived
curl -X GET "http://localhost:8000/spaces?exclude_types=personal&exclude_statuses=archived"

# Виключити декілька типів
curl -X GET "http://localhost:8000/spaces?exclude_types=personal,team"
```

---

## Архітектура

### SpaceService (оновлено)

**Нові методи:**

#### 1. `get_all_spaces()`
Отримує всі простори без пагінації (для метаданих).

```python
all_spaces = await service.get_all_spaces()
# Returns: List[Dict[str, Any]]
```

#### 2. `get_spaces_meta()`
Збирає унікальні типи та статуси.

```python
meta = await service.get_spaces_meta()
# Returns: {
#   "available_types": [...],
#   "available_statuses": [...]
# }
```

#### 3. `filter_spaces()`
Фільтрує список просторів за exclude_types та exclude_statuses.

```python
filtered = service.filter_spaces(
    spaces,
    exclude_types=["personal"],
    exclude_statuses=["archived"]
)
# Returns: List[Dict[str, Any]]
```

**Оновлений метод:**

#### `get_spaces()` - додані параметри
```python
result = await service.get_spaces(
    query=None,
    accessible_only=True,
    start=0,
    limit=25,
    exclude_types=["personal"],      # ⭐ НОВЕ
    exclude_statuses=["archived"]    # ⭐ НОВЕ
)
```

---

## Приклади використання

### Сценарій 1: Отримати доступні фільтри

```python
# 1. Отримати метадані
response = await client.get("/spaces/meta")
meta = response.json()

print(f"Available types: {meta['available_types']}")
print(f"Available statuses: {meta['available_statuses']}")

# 2. Побудувати UI з чекбоксами
for type in meta['available_types']:
    create_checkbox(f"Exclude {type}")
```

### Сценарій 2: Фільтрувати простори

```python
# Виключити personal та archived
response = await client.get(
    "/spaces",
    params={
        "exclude_types": "personal",
        "exclude_statuses": "archived"
    }
)

spaces = response.json()["spaces"]
print(f"Filtered spaces: {len(spaces)}")
```

### Сценарій 3: Динамічна фільтрація

```python
# Отримати всі типи
meta = await get_spaces_meta()

# Виключити всі типи крім global
exclude_types = [t for t in meta["available_types"] if t != "global"]

spaces = await get_spaces(exclude_types=exclude_types)
# Повертає тільки global простори
```

---

## Логіка фільтрації (OR)

### Таблиця істинності

| Space Type | Space Status | exclude_types=["personal"] | exclude_statuses=["archived"] | Виключений? |
|------------|--------------|---------------------------|------------------------------|-------------|
| global | current | ❌ | ❌ | ❌ НІ |
| personal | current | ✅ | ❌ | ✅ ТАК |
| global | archived | ❌ | ✅ | ✅ ТАК |
| personal | archived | ✅ | ✅ | ✅ ТАК |

**Висновок:** Простір виключається якщо **будь-яка** з умов виконується (OR логіка).

---

## Тестування

### Запуск тестів

```bash
# Всі тести для SpaceService
pytest tests/test_spaces_api.py -v
pytest tests/test_spaces_meta.py -v

# Конкретний тест
pytest tests/test_spaces_meta.py::test_get_spaces_meta -v

# З покриттям
pytest tests/test_spaces*.py --cov=src.services.space_service --cov-report=html
```

### Покриття тестами

**test_spaces_meta.py:**
- ✅ `test_get_all_spaces()` - пагінація
- ✅ `test_get_spaces_meta()` - збір метаданих
- ✅ `test_filter_spaces_by_types()` - фільтрація за типами
- ✅ `test_filter_spaces_by_statuses()` - фільтрація за статусами
- ✅ `test_filter_spaces_or_logic()` - OR логіка
- ✅ `test_filter_spaces_no_filters()` - без фільтрів
- ✅ `test_filter_spaces_multiple_types()` - декілька типів
- ✅ `test_get_spaces_with_filters()` - інтеграція з get_spaces
- ✅ `test_get_spaces_meta_empty()` - порожній список
- ✅ `test_get_spaces_meta_handles_none_values()` - None значення

**test_spaces_api.py (оновлено):**
- ✅ `test_get_spaces_with_exclude_types()` - фільтр типів
- ✅ `test_get_spaces_with_exclude_statuses()` - фільтр статусів
- ✅ `test_get_spaces_with_both_filters()` - обидва фільтри
- ✅ `test_get_spaces_with_multiple_exclude_types()` - декілька типів
- ✅ `test_get_spaces_no_filters()` - без фільтрів

---

## Структура коду

### Файли створені

1. ✅ `src/api/routers/spaces_meta.py` - роутер GET /spaces/meta
2. ✅ `tests/test_spaces_meta.py` - тести для метаданих

### Файли оновлені

1. ✅ `src/services/space_service.py` - додані методи
2. ✅ `src/api/routers/spaces.py` - додані параметри
3. ✅ `src/main.py` - зареєстровано spaces_meta_router
4. ✅ `tests/test_spaces_api.py` - додані тести для фільтрації

---

## Критерії приймання

✅ `/spaces/meta` повертає коректні списки типів та статусів  
✅ `/spaces` фільтрує простори згідно параметрів  
✅ Логіка OR: `type ∈ exclude_types` або `status ∈ exclude_statuses`  
✅ Всі тести проходять (10+ нових тестів)  
✅ Код типізований (Optional, List)  
✅ Логування працює  
✅ Немає синтаксичних помилок  

---

## Можливі розширення

1. **AND логіка** - параметр `filter_logic=AND|OR`
2. **Include фільтри** - `include_types`, `include_statuses`
3. **Regex фільтри** - `exclude_by_name_regex`
4. **Кешування метаданих** - для швидкого доступу
5. **Batch метадані** - `/spaces/meta/batch` для декількох просторів

---

## Приклади інтеграції з UI

### React приклад

```typescript
// Fetch metadata
const meta = await fetch('/spaces/meta').then(r => r.json());

// Build filters
const [excludeTypes, setExcludeTypes] = useState<string[]>([]);
const [excludeStatuses, setExcludeStatuses] = useState<string[]>([]);

// Fetch filtered spaces
const params = new URLSearchParams({
  exclude_types: excludeTypes.join(','),
  exclude_statuses: excludeStatuses.join(',')
});

const spaces = await fetch(`/spaces?${params}`).then(r => r.json());
```

### Vue приклад

```vue
<template>
  <div>
    <h3>Exclude Types:</h3>
    <div v-for="type in meta.available_types" :key="type">
      <label>
        <input type="checkbox" v-model="excludeTypes" :value="type" />
        {{ type }}
      </label>
    </div>
  </div>
</template>

<script setup>
const meta = ref({ available_types: [], available_statuses: [] });
const excludeTypes = ref([]);

onMounted(async () => {
  meta.value = await $fetch('/spaces/meta');
});

const filteredSpaces = computed(async () => {
  return await $fetch('/spaces', {
    params: {
      exclude_types: excludeTypes.value.join(',')
    }
  });
});
</script>
```

---

## Troubleshooting

### Проблема: Метадані порожні

**Причина:** Немає доступних просторів

**Рішення:**
```bash
# Перевірити доступ до Confluence
curl -X GET "http://localhost:8000/spaces"
```

### Проблема: Фільтри не працюють

**Причина:** Неправильний формат параметрів

**Рішення:**
```bash
# Правильно: comma-separated
curl -X GET "http://localhost:8000/spaces?exclude_types=personal,team"

# Неправильно: окремі параметри
curl -X GET "http://localhost:8000/spaces?exclude_types=personal&exclude_types=team"
```

### Проблема: OR замість AND логіки

**Очікування:** Виключити простори які є **і** personal **і** archived

**Реальність:** Виключаються простори які є **або** personal **або** archived

**Рішення:** Це очікувана поведінка (OR логіка). Для AND логіки потрібна нова реалізація.

---

## Summary

✅ **Створено:** 2 нові файли  
✅ **Оновлено:** 4 файли  
✅ **Тестів:** 10+ нових  
✅ **Рядків коду:** ~500  
✅ **Синтаксичних помилок:** 0  

**Система готова до використання!** 🚀
