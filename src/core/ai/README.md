# AI Provider Interface

## 📋 Опис

Базова абстракція для мульти-AI архітектури, яка забезпечує уніфікований інтерфейс для роботи з різними AI-провайдерами (OpenAI, Google Gemini, Anthropic Claude, тощо).

## 🏗️ Структура

### AIResponse

Pydantic-модель для стандартизованої відповіді від AI-провайдерів.

**Поля:**
- `text` (str, required) — Згенерований текст
- `provider` (str, required) — Ім'я провайдера (`openai`, `gemini`, `claude`)
- `model` (str, required) — Використана модель (`gpt-4o-mini`, `gemini-1.5-flash`)
- `raw` (dict, optional) — Сирий об'єкт відповіді (для debugging)
- `prompt_tokens` (int, optional) — Кількість токенів у prompt
- `completion_tokens` (int, optional) — Кількість токенів у відповіді
- `total_tokens` (int, optional) — Загальна кількість токенів

**Приклад:**
```python
from src.core.ai import AIResponse

response = AIResponse(
    text="This is AI-generated content",
    provider="openai",
    model="gpt-4o-mini",
    prompt_tokens=50,
    completion_tokens=100,
    total_tokens=150
)
```

### AIProvider

Protocol (інтерфейс) для всіх AI-провайдерів.

**Методи:**
- `async generate(prompt: str, **kwargs) -> AIResponse` — Генерація тексту
- `async embed(text: str, **kwargs) -> list[float]` — Створення embeddings
- `async count_tokens(text: str, **kwargs) -> int` — Підрахунок токенів

**Приклад реалізації:**
```python
from src.core.ai import AIProvider, AIResponse

class MyCustomProvider:
    name = "custom"
    
    async def generate(self, prompt: str, **kwargs) -> AIResponse:
        # Ваша логіка генерації
        return AIResponse(
            text="Generated response",
            provider=self.name,
            model="custom-model-v1"
        )
    
    async def embed(self, text: str, **kwargs) -> list[float]:
        # Ваша логіка embeddings
        return [0.1, 0.2, 0.3, ...]
    
    async def count_tokens(self, text: str, **kwargs) -> int:
        # Ваша логіка підрахунку токенів
        return len(text.split())
```

## 🧪 Тестування

Запуск тестів:
```bash
pytest tests/core/ai/test_interface.py -v
```

Всі тести повинні пройти успішно:
- ✅ Створення AIResponse з мінімальними полями
- ✅ Створення AIResponse з усіма полями
- ✅ Валідація обов'язкових полів
- ✅ Серіалізація у dict/JSON
- ✅ Робота з raw відповідями
- ✅ Реалізація AIProvider протоколу

## 🔄 Інтеграція

На даний момент це базові абстракції. Наступні кроки:

1. **Створити OpenAI Provider** — рефакторинг існуючої інтеграції
2. **Створити Gemini Provider** — нова інтеграція
3. **Створити AI Router** — маршрутизація між провайдерами
4. **Оновити Agents** — використання нового інтерфейсу

## 📖 Документація

Детальна документація архітектури: [docs/MULTI_AI_ARCHITECTURE.md](../../docs/MULTI_AI_ARCHITECTURE.md)

## ✅ Статус

- [x] AIResponse модель створено
- [x] AIProvider протокол визначено
- [x] Тести написано (10/10 passing)
- [x] **OpenAI Provider реалізовано (16/16 tests passing)**
- [x] **Gemini Provider реалізовано (24/24 tests passing)**
- [ ] AI Router (наступний крок)

**Загальна статистика:** ✅ 50/50 tests passing

---

## 🔌 Google Gemini Provider

### Використання

```python
from src.core.ai import GeminiClient, AIResponse

# Initialize client
client = GeminiClient(
    api_key="AIza...",  # Optional, reads from GEMINI_API_KEY or GOOGLE_API_KEY
    model_default="gemini-2.0-flash-exp"
)

# Generate text
response: AIResponse = await client.generate(
    prompt="Explain quantum computing in simple terms",
    temperature=0.7,
    max_tokens=500
)

print(response.text)  # Generated text
print(response.total_tokens)  # Token usage

# Count tokens
token_count = await client.count_tokens("Some text to count")
print(f"Tokens: {token_count}")
```

### Особливості

- ✅ **REST API based** — використовує Google Generative AI REST API v1beta
- ✅ **Rate limit handling** — автоматичні retry з exponential backoff
- ✅ **Token counting** — вбудована підтримка підрахунку токенів
- ✅ **Token tracking** — повна інформація про використання токенів
- ✅ **Error handling** — детальне логування помилок
- ✅ **Flexible configuration** — підтримка всіх Gemini параметрів
- ✅ **Protocol compliant** — реалізує AIProvider інтерфейс
- ✅ **Context manager support** — async with підтримка

### Підтримувані моделі

```python
# Gemini 2.0 (experimental)
client = GeminiClient(model_default="gemini-2.0-flash-exp")

# Gemini 1.5 (stable)
client = GeminiClient(model_default="gemini-1.5-pro")
client = GeminiClient(model_default="gemini-1.5-flash")

# Gemini 1.0
client = GeminiClient(model_default="gemini-1.0-pro")
```

### Конфігурація

```bash
# .env file
GEMINI_API_KEY=AIza...  # Preferred
# OR
GOOGLE_API_KEY=AIza...  # Alternative
```

### Generation Parameters

```python
response = await client.generate(
    prompt="Your prompt",
    temperature=0.7,       # Creativity (0.0 - 2.0)
    max_tokens=1000,       # Maximum output tokens
    top_p=0.95,           # Nucleus sampling
    top_k=40              # Top-k sampling
)
```

### Тести

```bash
pytest tests/core/ai/test_gemini_client.py -v
```

**Test coverage:**
- ✅ Initialization (6 tests)
  - With/without API key
  - Multiple env var names
  - Custom models and timeouts
- ✅ Text generation (9 tests)
  - Success cases
  - Custom models and parameters
  - Multiple text parts handling
  - Rate limit retry
  - Error handling
- ✅ Token counting (4 tests)
- ✅ Embeddings (1 test - placeholder)
- ✅ Protocol compliance (4 tests)

---

## 🔌 OpenAI Provider

### Використання

```python
from src.core.ai import OpenAIClient, AIResponse

# Initialize client
client = OpenAIClient(
    api_key="sk-...",  # Optional, reads from OPENAI_API_KEY env var
    model_default="gpt-4o-mini"
)

# Generate text
response: AIResponse = await client.generate(
    prompt="Explain quantum computing",
    temperature=0.7,
    max_tokens=500
)

print(response.text)  # Generated text
print(response.total_tokens)  # Token usage
```

### Особливості

- ✅ **Rate limit handling** — автоматичні retry з exponential backoff
- ✅ **Token tracking** — повна інформація про використання токенів
- ✅ **Error handling** — детальне логування помилок
- ✅ **Flexible configuration** — підтримка всіх OpenAI параметрів
- ✅ **Protocol compliant** — реалізує AIProvider інтерфейс

### Конфігурація

```bash
# .env file
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini  # Default model
```

### Тести

```bash
pytest tests/core/ai/test_openai_client.py -v
```

**Test coverage:**
- ✅ Initialization (with/without API key)
- ✅ Text generation (success, retries, errors)
- ✅ Rate limit handling
- ✅ Token counting (not implemented placeholder)
- ✅ Embeddings (not implemented placeholder)
- ✅ Protocol compliance

---
