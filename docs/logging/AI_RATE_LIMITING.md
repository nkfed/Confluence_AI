# AI Rate Limiting Documentation

## 📋 Огляд

Rate limiting захищає від помилок **429 (Too Many Requests)** при роботі з AI провайдерами (OpenAI, Gemini).

**SimpleRateLimiter** — локальний механізм контролю частоти запитів, який:
- ✅ Гарантує мінімальний інтервал між запитами
- ✅ Обмежує максимальну кількість запитів за хвилину (RPM)
- ✅ Блокує виконання через `time.sleep()` при перевищенні лімітів
- ✅ Використовує sliding window для точного відстеження

## 🎯 Навіщо потрібен Rate Limiter?

### Проблема: 429 Rate Limit Errors

```python
# Без rate limiter - швидко досягаємо ліміту
for i in range(100):
    response = await gemini_client.generate(f"Request {i}")
    # Після 10-15 запитів → 429 Error
```

### Рішення: Rate Limiter

```python
from src.core.ai.rate_limit import SimpleRateLimiter, RateLimitConfig

# Конфігурація для Gemini Free Tier
config = RateLimitConfig(max_rpm=10, min_interval_sec=0.5)
limiter = SimpleRateLimiter(config)

client = GeminiClient(api_key=..., rate_limiter=limiter)

# Безпечна обробка
for i in range(100):
    response = await client.generate(f"Request {i}")
    # Rate limiter автоматично контролює темп
```

## ⚙️ Конфігурація

### RateLimitConfig

```python
from src.core.ai.rate_limit import RateLimitConfig

config = RateLimitConfig(
    max_rpm=5,              # Максимум запитів за хвилину
    min_interval_sec=0.2    # Мінімальний інтервал між запитами (секунди)
)
```

**Параметри:**
- **max_rpm** — максимум запитів за хвилину (sliding window)
- **min_interval_sec** — мінімальний інтервал між запитами

### Рекомендовані налаштування

#### Gemini Free Tier
```python
# Conservative (безпечно для Free Tier)
config = RateLimitConfig(
    max_rpm=5,          # 5 запитів за хвилину
    min_interval_sec=1.0  # 1 секунда між запитами
)
```

#### Gemini Pay-as-you-go
```python
# Moderate (з оплатою)
config = RateLimitConfig(
    max_rpm=15,         # 15 запитів за хвилину
    min_interval_sec=0.5  # 0.5 секунди між запитами
)
```

#### OpenAI Free Tier
```python
# Conservative
config = RateLimitConfig(
    max_rpm=3,          # 3 запити за хвилину
    min_interval_sec=1.0  # 1 секунда між запитами
)
```

#### OpenAI Paid Tier 1
```python
# Normal usage
config = RateLimitConfig(
    max_rpm=60,         # 60 запитів за хвилину
    min_interval_sec=0.1  # 100ms між запитами
)
```

## 🚀 Використання

### 1. З GeminiClient

```python
from src.core.ai.gemini_client import GeminiClient
from src.core.ai.rate_limit import SimpleRateLimiter, RateLimitConfig

# Створення rate limiter
config = RateLimitConfig(max_rpm=10, min_interval_sec=0.5)
limiter = SimpleRateLimiter(config)

# Створення клієнта з rate limiter
client = GeminiClient(
    api_key="your-api-key",
    rate_limiter=limiter
)

# Використання (rate limiting автоматичний)
response = await client.generate("Your prompt")
```

### 2. З OpenAIClient

```python
from src.core.ai.openai_client import OpenAIClient
from src.core.ai.rate_limit import SimpleRateLimiter, RateLimitConfig

# Створення rate limiter
config = RateLimitConfig(max_rpm=60, min_interval_sec=0.1)
limiter = SimpleRateLimiter(config)

# Створення клієнта з rate limiter
client = OpenAIClient(
    api_key="your-api-key",
    rate_limiter=limiter
)

# Використання
response = await client.generate("Your prompt")
```

### 3. Без Rate Limiter (за замовчуванням)

```python
# Rate limiter опціональний
client = GeminiClient(api_key="your-api-key")

# Працює без обмежень (ризик 429)
response = await client.generate("Your prompt")
```

### 4. Спільний Rate Limiter

```python
# Один limiter для всіх клієнтів
config = RateLimitConfig(max_rpm=20, min_interval_sec=0.3)
limiter = SimpleRateLimiter(config)

openai_client = OpenAIClient(api_key=..., rate_limiter=limiter)
gemini_client = GeminiClient(api_key=..., rate_limiter=limiter)

# Обидва клієнти використовують один limiter
```

## 📊 Моніторинг

### Отримання статистики

```python
limiter = SimpleRateLimiter(config)

# ... після деяких запитів ...

stats = limiter.get_stats()
print(stats)
```

**Output:**
```python
{
    "requests_in_window": 5,          # Запитів у поточному вікні
    "max_rpm": 10,                    # Максимум RPM
    "window_age_sec": 25.3,           # Вік поточного вікна
    "window_remaining_sec": 34.7,     # До нового вікна
    "can_make_request": True,         # Чи можна зробити запит
    "last_call_ago_sec": 2.1          # Останній запит 2.1 сек тому
}
```

### Logging

```python
# Rate limiter автоматично логує
2025-12-30 18:42:48 | DEBUG | Rate limiter initialized: max_rpm=5, min_interval=0.2s
2025-12-30 18:42:49 | DEBUG | Rate limit check passed: request 1/5
2025-12-30 18:42:49 | DEBUG | Rate limit: sleeping 0.100s (min interval)
2025-12-30 18:42:50 | WARNING | Rate limit: RPM limit reached (5), sleeping 45.2s
```

## 🔧 Приклади використання

### Приклад 1: Bulk Tagging з Rate Limiting

```python
from src.core.ai.rate_limit import SimpleRateLimiter, RateLimitConfig
from src.agents.tagging_agent import TaggingAgent
from src.core.ai.router import AIProviderRouter
from src.core.ai.gemini_client import GeminiClient

# Rate limiter для Gemini Free Tier
config = RateLimitConfig(max_rpm=5, min_interval_sec=1.0)
limiter = SimpleRateLimiter(config)

# Gemini client з rate limiter
gemini = GeminiClient(api_key="...", rate_limiter=limiter)

# Router
router = AIProviderRouter(
    providers={"gemini": gemini},
    default_provider="gemini"
)

# Agent
tagging_agent = TaggingAgent(ai_router=router)

# Безпечна обробка сотень сторінок
pages = get_all_pages()  # 500+ сторінок

for page in pages:
    tags = await tagging_agent.suggest_tags(page.content)
    # Rate limiter автоматично контролює темп
    # Не отримаємо 429 помилок
```

### Приклад 2: Адаптивний Rate Limiting

```python
# Почати консервативно
config = RateLimitConfig(max_rpm=5, min_interval_sec=1.0)
limiter = SimpleRateLimiter(config)

client = GeminiClient(api_key="...", rate_limiter=limiter)

try:
    for i in range(100):
        response = await client.generate(f"Request {i}")
except RuntimeError as e:
    if "rate limit" in str(e).lower():
        # Зменшити темп
        limiter.config.max_rpm = 3
        limiter.config.min_interval_sec = 2.0
        print("Reduced rate limit due to 429 error")
```

### Приклад 3: Різні Limiters для різних Client

```python
# Conservative для Gemini Free
gemini_config = RateLimitConfig(max_rpm=5, min_interval_sec=1.0)
gemini_limiter = SimpleRateLimiter(gemini_config)
gemini_client = GeminiClient(api_key="...", rate_limiter=gemini_limiter)

# Aggressive для OpenAI Paid
openai_config = RateLimitConfig(max_rpm=60, min_interval_sec=0.1)
openai_limiter = SimpleRateLimiter(openai_config)
openai_client = OpenAIClient(api_key="...", rate_limiter=openai_limiter)

# Використання
gemini_response = await gemini_client.generate("...")  # Повільно
openai_response = await openai_client.generate("...")  # Швидко
```

## ⚠️ Важливо

### 1. Локальний Rate Limiting

⚠️ **SimpleRateLimiter** — це **локальний** механізм.

- ✅ Захищає від **локальних** перевищень
- ❌ НЕ синхронізується між процесами/машинами
- ❌ НЕ враховує інші додатки, що використовують той самий API key

**Для розподілених систем:**
- Використовуйте Redis-based rate limiter
- Або координуйте через централізовану систему

### 2. Blocking Behavior

⚠️ **Rate limiter блокує виконання** через `time.sleep()`.

```python
# Це заблокує поточний thread
limiter.before_call()  # Може зайняти до 60 секунд!
```

### 3. Overhead

Rate limiter додає невеликий overhead:
- **Мінімальний:** ~0.1ms на виклик (без блокування)
- **Максимальний:** до 60 секунд (при перевищенні RPM)

## 🎯 Best Practices

### 1. Почніть консервативно

```python
# Спочатку використовуйте низькі ліміти
config = RateLimitConfig(max_rpm=3, min_interval_sec=1.0)

# Поступово збільшуйте, якщо немає помилок
```

### 2. Моніторте статистику

```python
# Періодично перевіряйте
if limiter.get_stats()["requests_in_window"] >= limiter.config.max_rpm - 1:
    print("⚠️ Close to rate limit!")
```

### 3. Логіруйте помилки 429

```python
try:
    response = await client.generate(prompt)
except RuntimeError as e:
    if "429" in str(e) or "rate limit" in str(e).lower():
        logger.error("429 Error despite rate limiter!")
        # Можливо, потрібно зменшити ліміти
```

### 4. Використовуйте окремі limiters

```python
# НЕ спільний limiter для різних API keys
gemini_limiter = SimpleRateLimiter(config)
openai_limiter = SimpleRateLimiter(config)
```

### 5. Налаштуйте під Tier

| Provider | Tier | max_rpm | min_interval_sec |
|----------|------|---------|------------------|
| Gemini | Free | 5 | 1.0 |
| Gemini | Pay-as-go | 15 | 0.5 |
| OpenAI | Free | 3 | 1.0 |
| OpenAI | Tier 1 | 60 | 0.1 |
| OpenAI | Tier 2+ | 500+ | 0.01 |

## 🧪 Тестування

### Unit Tests

```bash
pytest tests/core/ai/test_rate_limit.py -v
```

**14 тестів:**
- ✅ Config initialization
- ✅ Min interval enforcement
- ✅ RPM limit enforcement
- ✅ Window reset
- ✅ Statistics
- ✅ Integration with Gemini
- ✅ Integration with OpenAI

### Manual Testing

```python
import asyncio
from src.core.ai.rate_limit import SimpleRateLimiter, RateLimitConfig

async def test_rate_limiter():
    config = RateLimitConfig(max_rpm=3, min_interval_sec=1.0)
    limiter = SimpleRateLimiter(config)
    
    for i in range(5):
        print(f"Request {i+1}...")
        start = time.time()
        limiter.before_call()
        elapsed = time.time() - start
        print(f"  Took {elapsed:.2f}s")
        
        stats = limiter.get_stats()
        print(f"  Stats: {stats['requests_in_window']}/{stats['max_rpm']}")

asyncio.run(test_rate_limiter())
```

## ✅ Переваги

1. ✅ **Простота** — легко інтегрувати
2. ✅ **Ефективність** — мінімальний overhead
3. ✅ **Гнучкість** — налаштовується під потреби
4. ✅ **Захист** — запобігає 429 помилкам
5. ✅ **Моніторинг** — статистика в реальному часі
6. ✅ **Опціональність** — можна не використовувати

## 🚀 Готово до використання!

Rate Limiter інтегрований у всі AI клієнти та готовий захищати ваші API запити від rate limit помилок!
