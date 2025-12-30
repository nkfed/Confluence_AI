# Prompt Engineering Guide

## Зміст

1. [Огляд системи промптів](#огляд-системи-промптів)
2. [Архітектура промптів](#архітектура-промптів)
3. [Створення нових промптів](#створення-нових-промптів)
4. [Налаштування параметрів](#налаштування-параметрів)
5. [Тестування промптів](#тестування-промптів)
6. [Best Practices](#best-practices)
7. [Troubleshooting](#troubleshooting)

---

## Огляд системи промптів

### Що таке промпт?

Промпт — це структурована інструкція для AI-моделі, яка визначає:
- **Роль агента** (хто ти є)
- **Завдання** (що потрібно зробити)
- **Обмеження** (які правила дотримуватись)
- **Формат виводу** (як повернути результат)

### Типи промптів у системі

```
src/prompts/
├── summary/           # Промпти для генерації резюме
│   ├── base.txt      # Базовий промпт (спільна частина)
│   ├── test.txt      # TEST режим
│   └── prod.txt      # PROD режим
│
└── tagging/          # Промпти для тегування
    ├── base.txt      # Базовий промпт
    ├── test.txt      # TEST режим
    ├── prod.txt      # PROD режим
    └── policy.txt    # Політика тегування
```

---

## Архітектура промптів

### 1. Модульна структура

Кожен промпт складається з **модулів**, які об'єднуються динамічно:

```python
final_prompt = base_template + dynamic_section + mode_template + content
```

#### Приклад: TaggingAgent

```
┌─────────────────────────────────────────────────────┐
│ base.txt                                            │
│ "Ти — TaggingAgent..."                             │
│ "Поверни JSON у форматі: {...}"                    │
└─────────────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────────────┐
│ DYNAMIC: ALLOWED TAGS (runtime)                     │
│ - doc-tech                                          │
│ - domain-helpdesk-site                             │
│ - kb-overview                                       │
└─────────────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────────────┐
│ DYNAMIC: LIMIT INSTRUCTION (from config)            │
│ "Для кожної категорії тегів пропонуй               │
│  не більше {MAX_TAGS_PER_CATEGORY} тегів"          │
└─────────────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────────────┐
│ test.txt / prod.txt                                 │
│ "# TEST режим" або "# PROD режим"                   │
└─────────────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────────────┐
│ CONTENT TO ANALYZE                                  │
│ {page_content}                                      │
└─────────────────────────────────────────────────────┘
```

### 2. PromptBuilder

**Файл:** `src/agents/prompt_builder.py`

PromptBuilder відповідає за:
- ✅ Завантаження шаблонів
- ✅ Динамічну генерацію інструкцій
- ✅ Об'єднання всіх частин
- ✅ Використання конфігурації

#### Методи

```python
class PromptBuilder:
    @staticmethod
    def build_tag_tree_prompt(
        content: str, 
        allowed_labels: List[str], 
        dry_run: bool = False
    ) -> str:
        """
        Будує промпт для /bulk/tag-tree з динамічним whitelist.
        
        Components:
        1. base.txt - базова структура
        2. ALLOWED TAGS - динамічний список тегів
        3. LIMIT INSTRUCTION - з конфігу
        4. TAGGING INSTRUCTION - правила тегування
        5. test.txt/prod.txt - режимний промпт
        6. CONTENT - контент для аналізу
        """
        pass
    
    @staticmethod
    def build_tag_pages_prompt(
        content: str, 
        dry_run: bool = False
    ) -> str:
        """
        Будує промпт для /bulk/tag-pages (legacy).
        
        Components:
        1. base.txt
        2. policy.txt - повна політика тегування
        3. LIMIT INSTRUCTION - з конфігу
        4. test.txt/prod.txt
        5. CONTENT
        """
        pass
```

### 3. PromptLoader

**Файл:** `src/utils/prompt_loader.py`

Утиліта для завантаження текстових шаблонів:

```python
class PromptLoader:
    @staticmethod
    def load(category: str, filename: str) -> str:
        """
        Завантажує промпт-шаблон з файлової системи.
        
        Args:
            category: Категорія (e.g., "tagging", "summary")
            filename: Ім'я файлу (e.g., "base.txt", "prod.txt")
            
        Returns:
            Текст шаблону
            
        Example:
            >>> base = PromptLoader.load("tagging", "base.txt")
            >>> prod = PromptLoader.load("tagging", "prod.txt")
        """
        pass
```

---

## Створення нових промптів

### Крок 1: Створіть файли шаблонів

```bash
# Створіть директорію для нового агента
mkdir src/prompts/new_agent

# Створіть базові файли
touch src/prompts/new_agent/base.txt
touch src/prompts/new_agent/test.txt
touch src/prompts/new_agent/prod.txt
```

### Крок 2: Напишіть base.txt

```plaintext
Ти — NewAgent. Твоє завдання — [опис завдання].

ВАЖЛИВО:
[Ключові правила та обмеження]

Поверни результат у форматі:
{
  "field1": "...",
  "field2": "..."
}

Інструкції:
{INSTRUCTIONS}

Вхідні дані:
{INPUT}
```

**Рекомендації для base.txt:**
- ✅ Чітко визначте роль агента
- ✅ Вкажіть формат виводу (JSON recommended)
- ✅ Використовуйте плейсхолдери: `{VARIABLE}`
- ✅ Мова: українська (для consistency)

### Крок 3: Напишіть test.txt

```plaintext
# TEST режим
Використовуй спрощений набір даних для тестування.

ВАЖЛИВО:
[Додаткові обмеження для TEST режиму]
```

**Рекомендації для test.txt:**
- ✅ Вкажіть спрощені правила
- ✅ Додайте debugging-інструкції
- ✅ Обмежте scope операцій

### Крок 4: Напишіть prod.txt

```plaintext
# PROD режим
Використовуй повний набір правил та даних.

ВАЖЛИВО:
[Правила для production]
```

**Рекомендації для prod.txt:**
- ✅ Повні інструкції
- ✅ Production-ready правила
- ✅ Оптимізація для якості

### Крок 5: Створіть Builder Method

```python
# src/agents/prompt_builder.py

@staticmethod
def build_new_agent_prompt(
    content: str, 
    config_param: str,
    dry_run: bool = False
) -> str:
    """
    Build prompt for NewAgent.
    
    Args:
        content: Input content to process
        config_param: Dynamic configuration
        dry_run: If True, use test.txt mode
        
    Returns:
        Complete prompt string
    """
    # Load templates
    base = PromptLoader.load("new_agent", "base.txt")
    mode = "test.txt" if dry_run else "prod.txt"
    mode_template = PromptLoader.load("new_agent", mode)
    
    # Build dynamic instructions
    instructions = f"Process using {config_param}"
    
    # Combine
    prompt = f"""{base}

{instructions}

{mode_template}

INPUT:
{content[:5000]}
"""
    
    return prompt
```

### Крок 6: Додайте до агента

```python
# src/agents/new_agent.py

class NewAgent(BaseAgent):
    def __init__(self):
        super().__init__(agent_name="NEW_AGENT")
        self.ai = OpenAIClient()
    
    async def process(self, content: str, config: str) -> dict:
        # Build prompt using PromptBuilder
        prompt = PromptBuilder.build_new_agent_prompt(
            content=content,
            config_param=config,
            dry_run=self.is_dry_run()
        )
        
        # Call AI
        response = await self.ai.generate(prompt)
        
        # Parse and return
        return self._parse_response(response)
```

---

## Налаштування параметрів

### 1. Централізований конфіг

**Файл:** `src/config/tagging_settings.py`

```python
"""
Централізовані налаштування для системи тегування.
"""

# Максимальна кількість тегів на категорію
MAX_TAGS_PER_CATEGORY = 3

# Категорії тегів
TAG_CATEGORIES = ["doc", "domain", "kb", "tool"]

# Опис категорій
TAG_CATEGORY_DESCRIPTIONS = {
    "doc": "Тип документа",
    "domain": "Домен/проєкт",
    "kb": "Роль у базі знань",
    "tool": "Інструменти/технології"
}
```

### 2. Використання конфігу в промптах

```python
from src.config.tagging_settings import MAX_TAGS_PER_CATEGORY, TAG_CATEGORIES

# Dynamic instruction generation
limit_instruction = f"""
ВАЖЛИВО:
Для кожної категорії тегів ({", ".join(TAG_CATEGORIES)}) 
пропонуй не більше {MAX_TAGS_PER_CATEGORY} найбільш релевантних тегів.
"""
```

### 3. Використання в коді

```python
from src.config.tagging_settings import MAX_TAGS_PER_CATEGORY

def limit_tags_per_category(tags: dict) -> dict:
    """Обмежує кількість тегів згідно з конфігом."""
    limited = {}
    for category in TAG_CATEGORIES:
        tag_list = tags.get(category, [])
        limited[category] = tag_list[:MAX_TAGS_PER_CATEGORY]
    return limited
```

### 4. Як змінити налаштування

**Scenario: Потрібно обмежити до 2 тегів на категорію**

```python
# src/config/tagging_settings.py

# BEFORE
MAX_TAGS_PER_CATEGORY = 3

# AFTER
MAX_TAGS_PER_CATEGORY = 2
```

**Result:**
- ✅ Промпти автоматично: "не більше 2 тегів"
- ✅ Post-processing: `tags[:2]`
- ✅ Всі endpoints оновлені
- ✅ Не потрібно змінювати код!

---

## Тестування промптів

### 1. Unit Tests для PromptBuilder

```python
# tests/test_prompt_builder.py

def test_prompt_includes_config():
    """Перевірка що промпт містить значення з конфігу."""
    prompt = PromptBuilder.build_tag_tree_prompt(
        content="Test content",
        allowed_labels=["doc-tech"],
        dry_run=True
    )
    
    # Verify config values in prompt
    assert str(MAX_TAGS_PER_CATEGORY) in prompt
    assert "не більше" in prompt
```

### 2. Integration Tests

```python
# tests/test_tagging_agent.py

@pytest.mark.asyncio
async def test_agent_respects_limit():
    """Перевірка що агент дотримується ліміту."""
    agent = TaggingAgent()
    
    large_text = """
    [Текст з багатьма потенційними тегами]
    """
    
    tags = await agent.suggest_tags(large_text)
    
    # Verify limits
    for category, tag_list in tags.items():
        assert len(tag_list) <= MAX_TAGS_PER_CATEGORY
```

### 3. Manual Testing

```bash
# 1. Запустіть сервер
python run_server.py

# 2. Викличте endpoint
curl -X POST "http://localhost:8000/pages/12345/auto-tag?dry_run=true"

# 3. Перевірте response
# tags.proposed має містити ≤ MAX_TAGS_PER_CATEGORY тегів на категорію
```

### 4. A/B Testing промптів

```python
# tests/test_prompt_variations.py

@pytest.mark.asyncio
async def test_compare_prompts():
    """Порівняння різних версій промпту."""
    
    # Version A: Current
    prompt_a = PromptBuilder.build_tag_tree_prompt(
        content=TEST_CONTENT,
        allowed_labels=TEST_LABELS,
        dry_run=True
    )
    
    # Version B: Experimental
    prompt_b = build_experimental_prompt(
        content=TEST_CONTENT,
        allowed_labels=TEST_LABELS
    )
    
    # Compare results
    result_a = await ai.generate(prompt_a)
    result_b = await ai.generate(prompt_b)
    
    print(f"Version A: {result_a}")
    print(f"Version B: {result_b}")
    
    # Analyze which is better
```

---

## Best Practices

### 1. Структура промпту

✅ **DO:**
```plaintext
Ти — [Role]. Твоє завдання — [Task].

ВАЖЛИВО:
- Правило 1
- Правило 2

Формат виводу:
{...}

Дані для аналізу:
[Content]
```

❌ **DON'T:**
```plaintext
Проаналізуй це і поверни результат
[Content]
```

### 2. Мова промптів

✅ **Рекомендовано: Українська**
- Консистентність у всіх промптах
- Легше підтримувати
- Зрозуміло для команди

```plaintext
Ти — TaggingAgent. Твоє завдання — визначити теги...

ВАЖЛИВО:
Для кожної категорії тегів...
```

❌ **Не рекомендовано: Мікс мов**
```plaintext
You are TaggingAgent. Твоє завдання...
Important: Для кожної категорії...
```

### 3. Плейсхолдери

✅ **Чіткі плейсхолдери:**
```plaintext
Політика:
{POLICY}

Дозволені теги:
{ALLOWED_TAGS}

Текст:
{TEXT}
```

### 4. Обмеження

✅ **Explicit limits:**
```python
limit_instruction = f"""
Пропонуй не більше {MAX_TAGS_PER_CATEGORY} тегів на категорію.
"""
```

✅ **Post-processing backup:**
```python
# AI може не дотриматись, тому обрізаємо
limited = tags[:MAX_TAGS_PER_CATEGORY]
```

### 5. Режими роботи

**TEST режим:**
- ✅ Спрощені правила
- ✅ Менше даних
- ✅ Швидше виконання
- ✅ Debugging-friendly

**PROD режим:**
- ✅ Повні інструкції
- ✅ Всі дані
- ✅ Максимальна якість
- ✅ Production-ready

### 6. Версіонування

```plaintext
# v1.0 - Initial version
# v1.1 - Added MAX_TAGS_PER_CATEGORY limit
# v1.2 - Translated to Ukrainian
# v2.0 - Modular structure with PromptBuilder
```

---

## Troubleshooting

### Проблема 1: AI не дотримується формату

**Симптоми:**
- AI повертає текст замість JSON
- JSON неправильний

**Рішення:**
```plaintext
# Додайте на початок промпту
Твоє завдання — повернути ТІЛЬКИ JSON.
Не додавай пояснень, markdown або тексту поза JSON.

# Додайте в кінець
Return ONLY JSON. No explanations.
```

### Проблема 2: AI ігнорує обмеження

**Симптоми:**
- AI повертає більше ніж `MAX_TAGS_PER_CATEGORY` тегів

**Рішення:**
```python
# Додайте post-processing
tags = await agent.suggest_tags(text)
limited_tags = limit_tags_per_category(tags)  # ✅ Жорстке обмеження
```

### Проблема 3: Промпт занадто довгий

**Симптоми:**
- Token limit exceeded
- Повільна обробка

**Рішення:**
```python
# Обрізайте контент
content = page_content[:5000]  # Перші 5000 символів

# Або використовуйте chunking
chunks = split_into_chunks(page_content, max_size=4000)
```

### Проблема 4: Різні результати для однакового контенту

**Симптоми:**
- AI повертає різні теги для того самого тексту

**Рішення:**
```python
# Додайте temperature control
response = await ai.generate(prompt, temperature=0.3)  # ✅ Більш детерміновано
```

### Проблема 5: AI створює нові теги

**Симптоми:**
- AI вигадує теги, яких немає в whitelist

**Рішення:**
```plaintext
# Підкресліть у промпті
КРИТИЧНО ВАЖЛИВО:
Використовуй ТІЛЬКИ теги зі списку ALLOWED TAGS.
НЕ створюй нових тегів.
НЕ використовуй теги, яких немає у списку.

# + Post-processing filter
allowed_set = set(allowed_labels)
filtered_tags = [tag for tag in tags if tag in allowed_set]
```

---

## Приклади

### Приклад 1: Простий промпт

```plaintext
# src/prompts/example/base.txt

Ти — ClassificationAgent.

Твоє завдання:
Класифікуй документ за типом.

Можливі типи:
- technical
- business
- process

Поверни JSON:
{
  "type": "..."
}

Текст:
{TEXT}
```

### Приклад 2: Складний промпт з динамікою

```python
# PromptBuilder method

@staticmethod
def build_classification_prompt(content: str, types: List[str]) -> str:
    base = PromptLoader.load("classification", "base.txt")
    
    # Dynamic types list
    types_section = "Можливі типи:\n" + "\n".join(f"- {t}" for t in types)
    
    prompt = f"""{base}

{types_section}

Текст:
{content[:5000]}
"""
    
    return prompt
```

### Приклад 3: Режимний промпт

```python
# Agent usage

class MyAgent(BaseAgent):
    async def process(self, content: str) -> dict:
        # Automatically selects test.txt or prod.txt
        dry_run = self.is_dry_run()
        
        prompt = PromptBuilder.build_my_prompt(
            content=content,
            dry_run=dry_run
        )
        
        return await self.ai.generate(prompt)
```

---

## Корисні ресурси

### Документація OpenAI
- [Prompt Engineering Guide](https://platform.openai.com/docs/guides/prompt-engineering)
- [Best Practices](https://help.openai.com/en/articles/6654000-best-practices-for-prompt-engineering)

### Внутрішні документи
- [Agent Development Guide](./AGENT_DEVELOPMENT.md)
- [Testing Guide](./TESTING.md)
- [API Documentation](./API.md)

### Приклади коду
- `src/agents/tagging_agent.py` - Повний приклад агента
- `src/agents/prompt_builder.py` - Приклади builders
- `tests/test_tagging_agent.py` - Приклади тестів

---

## Чеклист для нового промпту

- [ ] Створено файли: `base.txt`, `test.txt`, `prod.txt`
- [ ] Base промпт містить:
  - [ ] Чітку роль агента
  - [ ] Опис завдання
  - [ ] Формат виводу
  - [ ] Плейсхолдери для динамічних даних
- [ ] Створено builder method у `PromptBuilder`
- [ ] Додано використання конфігу (якщо потрібно)
- [ ] Написано unit tests для builder
- [ ] Написано integration tests для агента
- [ ] Протестовано в TEST режимі
- [ ] Протестовано в PROD режимі
- [ ] Задокументовано у цьому файлі
- [ ] Code review пройдено

---

## Історія змін

| Дата | Версія | Зміни |
|------|--------|-------|
| 2025-12-27 | 1.0 | Початкова версія документації |
| 2025-12-27 | 1.1 | Додано розділ про централізований конфіг |
| 2025-12-27 | 1.2 | Додано приклади та troubleshooting |

---

**Автор:** Confluence AI Team  
**Останнє оновлення:** 27 грудня 2025  
**Статус:** ✅ Production Ready
