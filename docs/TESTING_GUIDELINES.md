# Testing Guidelines

## 📋 Зміст

1. [Розташування тестів](#розташування-тестів)
2. [Структура тестів](#структура-тестів)
3. [Naming Conventions](#naming-conventions)
4. [Best Practices](#best-practices)
5. [Running Tests](#running-tests)

---

## 📁 Розташування тестів

### ✅ ПРАВИЛО: Всі тести у папці `tests/`

**Обов'язкове правило:** Усі тестові файли повинні знаходитися **виключно** у папці `tests/`.

```
Confluence_AI/
├── src/                    # ✅ Продакшн код
│   ├── agents/
│   ├── services/
│   └── ...
├── tests/                  # ✅ ВСІ тести тут
│   ├── test_agents.py
│   ├── test_services.py
│   └── ...
└── run_tests.py           # ✅ Test runner (не тест!)
```

### ❌ ЗАБОРОНЕНО: Тести в кореневій папці

```
Confluence_AI/
├── test_something.py      # ❌ ЗАБОРОНЕНО!
├── test_feature.py        # ❌ ЗАБОРОНЕНО!
└── tests/                 # ✅ Правильне місце
```

### Чому це важливо?

1. ✅ **Організація** - Всі тести в одному місці
2. ✅ **Чистота проєкту** - Коренева папка не захаращена
3. ✅ **CI/CD** - Легко налаштувати автоматичні тести
4. ✅ **IDE Integration** - VS Code та інші IDE автоматично знаходять тести
5. ✅ **pytest Discovery** - pytest автоматично знаходить всі тести в `tests/`

---

## 🏗️ Структура тестів

### Організація файлів

```
tests/
├── __init__.py                          # Порожній файл (для Python package)
│
├── test_agents/                         # Тести для агентів (optional grouping)
│   ├── test_tagging_agent.py
│   ├── test_summary_agent.py
│   └── test_base_agent.py
│
├── test_services/                       # Тести для сервісів (optional grouping)
│   ├── test_bulk_tagging_service.py
│   └── test_confluence_service.py
│
├── test_api/                            # Тести для API endpoints
│   ├── test_health.py
│   └── test_bulk.py
│
├── test_utils/                          # Тести для утиліт
│   ├── test_tag_structure.py
│   └── test_prompt_loader.py
│
└── conftest.py                          # pytest fixtures (спільні для всіх тестів)
```

### Flat Structure (Поточна)

Також допустима flat структура (всі файли в одній папці):

```
tests/
├── __init__.py
├── conftest.py
├── test_tagging_agent.py
├── test_summary_agent.py
├── test_bulk_tagging_service.py
├── test_confluence_service.py
├── test_tag_structure.py
└── ...
```

**Рекомендація:** Flat structure для малих/середніх проєктів, вкладена для великих.

---

## 📝 Naming Conventions

### Імена файлів

✅ **ПРАВИЛЬНО:**
```
test_tagging_agent.py
test_bulk_tagging_service.py
test_tag_structure.py
test_centralized_tagging_config.py
```

❌ **НЕПРАВИЛЬНО:**
```
tagging_agent_test.py        # test_ має бути на початку
test-tagging-agent.py         # Використовуй _ замість -
TestTaggingAgent.py           # Lowercase з underscores
tagging_test.py               # Занадто загальне
```

### Імена тест-функцій

✅ **ПРАВИЛЬНО:**
```python
def test_agent_suggests_correct_tags():
    ...

def test_limit_tags_per_category():
    ...

def test_tag_tree_root_page_tag_limit():
    ...

@pytest.mark.asyncio
async def test_bulk_tagging_service_processes_tree():
    ...
```

❌ **НЕПРАВИЛЬНО:**
```python
def testAgentSuggestsTags():              # Використовуй snake_case
    ...

def test_it_works():                      # Занадто загальне
    ...

def verify_tags():                        # Має починатися з test_
    ...
```

### Імена класів тестів (optional)

Якщо групуєш тести в класи:

✅ **ПРАВИЛЬНО:**
```python
class TestTaggingAgent:
    def test_suggest_tags(self):
        ...
    
    def test_parse_response(self):
        ...

class TestBulkTaggingService:
    def test_tag_tree(self):
        ...
    
    def test_tag_space(self):
        ...
```

---

## 🎯 Best Practices

### 1. Один тестовий файл на модуль

```
src/agents/tagging_agent.py     →  tests/test_tagging_agent.py
src/services/bulk_service.py    →  tests/test_bulk_service.py
src/utils/tag_structure.py      →  tests/test_tag_structure.py
```

### 2. Групування тестів

**За функціональністю:**
```python
# test_tagging_agent.py

def test_suggest_tags_with_valid_input():
    ...

def test_suggest_tags_with_empty_input():
    ...

def test_suggest_tags_respects_max_limit():
    ...
```

**За сценаріями:**
```python
# test_tag_tree_scenarios.py

def test_tag_tree_with_small_tree():
    ...

def test_tag_tree_with_large_tree():
    ...

def test_tag_tree_with_empty_root():
    ...
```

### 3. Використання fixtures

**conftest.py:**
```python
import pytest
from src.clients.confluence_client import ConfluenceClient

@pytest.fixture
def confluence_client():
    """Shared fixture for all tests."""
    return ConfluenceClient()

@pytest.fixture
def sample_page_content():
    """Sample content for testing."""
    return "Technical documentation about AI integration..."
```

**test_file.py:**
```python
def test_something(confluence_client, sample_page_content):
    # Use fixtures
    result = confluence_client.process(sample_page_content)
    assert result is not None
```

### 4. Async Tests

```python
import pytest

@pytest.mark.asyncio
async def test_async_function():
    result = await some_async_function()
    assert result == expected
```

### 5. Markers для групування

```python
import pytest

@pytest.mark.unit
def test_unit_functionality():
    ...

@pytest.mark.integration
async def test_integration_scenario():
    ...

@pytest.mark.slow
def test_slow_operation():
    ...
```

**Запуск:**
```bash
pytest -m unit              # Тільки unit тести
pytest -m integration       # Тільки integration тести
pytest -m "not slow"        # Всі крім slow
```

### 6. Parametrize для множинних входів

```python
import pytest

@pytest.mark.parametrize("input,expected", [
    ("doc-tech", "doc"),
    ("domain-helpdesk-site", "domain"),
    ("kb-overview", "kb"),
    ("tool-rovo-agent", "tool"),
])
def test_extract_category(input, expected):
    result = extract_category(input)
    assert result == expected
```

### 7. Docstrings для складних тестів

```python
def test_tag_tree_root_page_tag_limit():
    """
    Перевірка що обмеження ≤MAX_TAGS_PER_CATEGORY застосовується до ROOT сторінки.
    
    Проблема:
    - Root page мала 15+ тегів (не обмежені)
    - Дочірні сторінки мали правильне обмеження
    
    Expected після fix:
    - Root page має ≤3 теги на категорію
    - Дочірні сторінки теж ≤3 теги
    """
    ...
```

---

## 🚀 Running Tests

### Всі тести

```bash
pytest tests/
```

### Конкретний файл

```bash
pytest tests/test_tagging_agent.py
```

### Конкретний тест

```bash
pytest tests/test_tagging_agent.py::test_suggest_tags
```

### З verbose output

```bash
pytest tests/ -v
```

### З stdout (print statements)

```bash
pytest tests/ -v -s
```

### Parallel execution

```bash
pytest tests/ -n auto
```

### Coverage report

```bash
pytest tests/ --cov=src --cov-report=html
```

### Використання pytest.ini

**pytest.ini** (у кореневій папці):
```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
asyncio_mode = auto
markers =
    unit: Unit tests
    integration: Integration tests
    slow: Slow tests
```

---

## 📋 Checklist для нового тесту

При створенні нового тесту переконайся:

- [ ] Файл створено в папці `tests/`
- [ ] Ім'я файлу починається з `test_`
- [ ] Ім'я функції починається з `test_`
- [ ] Використано `snake_case` для імен
- [ ] Додано docstring для складних тестів
- [ ] Використано fixtures де можливо
- [ ] Async тести мають `@pytest.mark.asyncio`
- [ ] Тест ізольований (не залежить від інших тестів)
- [ ] Тест повторюваний (детерміністичний)
- [ ] Додано assertions для перевірки результатів

---

## 🔧 Maintenance

### Періодична перевірка

Запусти цю команду для перевірки що всі тести в правильному місці:

```powershell
# Перевірка на тести в кореневій папці
Get-ChildItem -Path "." -Filter "test_*.py" -File

# Якщо повертає файли - перенеси їх:
Move-Item -Path "test_*.py" -Destination "tests\" -Force
```

### Git pre-commit hook (optional)

Створи `.git/hooks/pre-commit`:

```bash
#!/bin/sh
# Check for test files in root directory
if ls test_*.py 1> /dev/null 2>&1; then
    echo "Error: Test files found in root directory!"
    echo "Please move them to tests/ directory"
    exit 1
fi
```

---

## 📚 Додаткові ресурси

### pytest Documentation
- [pytest.org](https://docs.pytest.org/)
- [pytest fixtures](https://docs.pytest.org/en/stable/fixture.html)
- [pytest markers](https://docs.pytest.org/en/stable/mark.html)

### Внутрішні документи
- [Prompt Engineering Guide](./PROMPT_ENGINEERING.md)
- [Agent Development Guide](./agent-mode-system.md)
- [Logging Guide](./logging_guide.md)

---

## 📝 Історія змін

| Дата | Зміна |
|------|-------|
| 2025-12-27 | Створення документа |
| 2025-12-27 | Переміщення 7 тестових файлів з root до tests/ |

---

**Автор:** Confluence AI Team  
**Останнє оновлення:** 27 грудня 2025  
**Статус:** ✅ Active Rule
