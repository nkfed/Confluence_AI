# AI Error Handling Documentation

## 📋 Огляд

**Error Handling Layer** — це стандартизована система обробки помилок для AI провайдерів з автоматичним fallback механізмом.

**Ключові можливості:**
- ✅ Кастомні винятки для різних сценаріїв
- ✅ Автоматичний fallback при збоях
- ✅ Чітка ієрархія помилок
- ✅ Детальна інформація про помилки
- ✅ Передбачувана поведінка
- ✅ Легка обробка в бізнес-логіці

## 🎯 Навіщо потрібен Error Handling?

### Проблема: Непередбачувані помилки

```python
# Без стандартизованих помилок
try:
    result = await router.generate("prompt")
except Exception as e:
    # Що це за помилка?
    # Чи варто робити retry?
    # Чи fallback спрацював?
    # 🤷 Невідомо!
    logger.error(f"Error: {e}")
```

### Рішення: Typed Exceptions

```python
from src.core.ai.errors import (
    ProviderUnavailableError,
    FallbackFailedError,
)

try:
    result = await router.generate("prompt")
    
except ProviderUnavailableError as e:
    # ✅ Зрозуміло: провайдер недоступний
    # Можна спробувати іншого
    logger.error(f"Provider unavailable: {e}")
    
except FallbackFailedError as e:
    # ✅ Зрозуміло: обидва провайдери провалилися
    # Критична помилка, треба алертити
    logger.critical(f"All providers failed: {e}")
    send_alert(e)
```

## 🔥 Винятки

### 1. AIProviderError (Base)

**Базовий виняток** для всіх AI provider помилок.

```python
class AIProviderError(Exception):
    """Base exception for all AI provider-related errors"""
    pass
```

**Використання:**
```python
# Catch all AI provider errors
try:
    result = await router.generate("prompt")
except AIProviderError as e:
    logger.error(f"AI provider error: {e}")
    # Handle any AI error
```

### 2. RateLimitError

**Перевищено ліміт запитів** до API.

```python
class RateLimitError(AIProviderError):
    """Exception raised when API rate limit is exceeded"""
    pass
```

**Коли виникає:**
- Забагато запитів за короткий час
- Rate limiter не був використаний
- Несподіваний сплеск трафіку

**Як обробляти:**
```python
from src.core.ai.errors import RateLimitError
import asyncio

try:
    result = await client.generate("prompt")
except RateLimitError:
    logger.warning("Rate limit exceeded, waiting...")
    await asyncio.sleep(60)  # Wait 1 minute
    result = await client.generate("prompt")  # Retry
```

### 3. ProviderUnavailableError

**Провайдер недоступний** або не сконфігурований.

```python
class ProviderUnavailableError(AIProviderError):
    """Exception raised when AI provider is unavailable or not configured"""
    pass
```

**Коли виникає:**
- Provider не зареєстрований в router
- API key відсутній або невалідний
- Provider service недоступний (downtime)
- Проблеми з мережею
- Primary провайдер провалився і немає fallback

**Як обробляти:**
```python
from src.core.ai.errors import ProviderUnavailableError

try:
    result = await router.generate("prompt", provider="openai")
except ProviderUnavailableError as e:
    logger.error(f"OpenAI unavailable: {e}")
    # Try alternative provider
    result = await router.generate("prompt", provider="gemini")
```

### 4. FallbackFailedError

**Обидва провайдери провалилися** (primary і fallback).

```python
class FallbackFailedError(AIProviderError):
    """Exception raised when both primary and fallback providers fail"""
    pass
```

**Коли виникає:**
- Primary провайдер провалився
- Fallback провайдер також провалився
- Критична ситуація

**Як обробляти:**
```python
from src.core.ai.errors import FallbackFailedError

try:
    result = await router.generate("prompt")
except FallbackFailedError as e:
    logger.critical(f"All providers failed: {e}")
    # Send alert to operations team
    send_alert("Critical: All AI providers failed", str(e))
    # Return error to user
    return {"error": "AI service temporarily unavailable"}
```

## 🔄 Fallback Логіка

### Як працює fallback

```
┌─────────────────────────────────────────────────┐
│ 1. User calls router.generate("prompt")        │
└───────────────┬─────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────────────┐
│ 2. Try PRIMARY provider (e.g., OpenAI)         │
└───────────┬─────────────────┬───────────────────┘
            │                 │
         SUCCESS           FAILURE
            │                 │
            ▼                 ▼
    ┌───────────┐   ┌──────────────────────────────┐
    │  Return   │   │ 3. Check if fallback exists  │
    │  Result   │   └────────┬────────────┬────────┘
    └───────────┘            │            │
                          YES           NO
                            │            │
                            ▼            ▼
              ┌──────────────────┐  ┌─────────────────────────┐
              │ 4. Try FALLBACK  │  │ Raise                   │
              │    (e.g., Gemini)│  │ ProviderUnavailableError│
              └────┬────────┬────┘  └─────────────────────────┘
                   │        │
                SUCCESS  FAILURE
                   │        │
                   ▼        ▼
           ┌───────────┐  ┌─────────────────┐
           │  Return   │  │ Raise           │
           │  Result   │  │ FallbackFailed  │
           └───────────┘  │ Error           │
                          └─────────────────┘
```

### Сценарії

#### Scenario 1: Primary → OK ✅

```python
router = AIProviderRouter(
    default_provider="openai",
    fallback_provider="gemini"
)

# OpenAI працює
result = await router.generate("Hello")
# ✅ Success with OpenAI
# Fallback не викликається
```

**Лог:**
```
INFO Generating with provider: openai
INFO Successfully generated with openai
```

#### Scenario 2: Primary → Error → Fallback → OK ✅

```python
router = AIProviderRouter(
    default_provider="openai",
    fallback_provider="gemini"
)

# OpenAI падає, Gemini працює
result = await router.generate("Hello")
# ✅ Success with Gemini (fallback)
```

**Лог:**
```
INFO Generating with provider: openai
WARNING Provider openai failed: Rate limit exceeded
INFO Attempting fallback to: gemini
INFO Successfully generated with fallback gemini
```

#### Scenario 3: Primary → Error → Fallback → Error ❌

```python
router = AIProviderRouter(
    default_provider="openai",
    fallback_provider="gemini"
)

# Обидва падають
try:
    result = await router.generate("Hello")
except FallbackFailedError as e:
    # ❌ Both failed
    logger.critical(f"Critical error: {e}")
```

**Лог:**
```
INFO Generating with provider: openai
WARNING Provider openai failed: Rate limit exceeded
INFO Attempting fallback to: gemini
ERROR Fallback provider gemini also failed: Service unavailable
```

#### Scenario 4: Primary → Error → No Fallback ❌

```python
router = AIProviderRouter(
    default_provider="openai",
    fallback_provider=None  # No fallback
)

# OpenAI падає, fallback немає
try:
    result = await router.generate("Hello")
except ProviderUnavailableError as e:
    # ❌ Primary failed, no fallback
    logger.error(f"Provider unavailable: {e}")
```

**Лог:**
```
INFO Generating with provider: openai
WARNING Provider openai failed: Rate limit exceeded
```

#### Scenario 5: Fallback Same as Primary ❌

```python
router = AIProviderRouter(
    default_provider="openai",
    fallback_provider="openai"  # Same!
)

# OpenAI падає, fallback той самий
try:
    result = await router.generate("Hello")
except ProviderUnavailableError as e:
    # ❌ Primary failed, fallback not attempted
    logger.error(f"Provider unavailable: {e}")
```

**Логіка:** Якщо fallback той самий що і primary, немає сенсу його викликати.

## 🎯 Best Practices

### 1. Не ловити AIProviderError в бізнес-логіці

```python
# ❌ Bad: Catching too broadly
async def generate_summary(page_id):
    try:
        result = await router.generate(prompt)
        return result.text
    except Exception:
        # Too generic, hides real issues
        return "Error"

# ✅ Good: Let errors propagate
async def generate_summary(page_id):
    # Let AIProviderError propagate
    result = await router.generate(prompt)
    return result.text

# Handle at higher level
try:
    summary = await generate_summary(page_id)
except FallbackFailedError:
    # Send alert
    send_alert("AI service down")
except ProviderUnavailableError:
    # Try alternative approach
    summary = get_cached_summary(page_id)
```

### 2. Логувати через unified logging

```python
from src.core.ai.logging_utils import log_ai_call

# ✅ Good: Unified logging captures errors
result = await log_ai_call(
    provider_name="openai",
    model="gpt-4o-mini",
    operation="summary",
    coro=lambda: provider.generate(prompt)
)
# Errors are automatically logged with context
```

### 3. Використовувати health check перед запуском

```python
from src.core.ai.router import AIProviderRouter

router = AIProviderRouter()

# ✅ Good: Check health first
report = await router.explain()

if not report['all_providers_ok']:
    logger.warning("Some providers unhealthy!")
    # Decide whether to proceed

# Start processing
result = await router.generate(prompt)
```

### 4. Використовувати rate limit guard

```python
from src.core.ai.rate_limit import SimpleRateLimiter

# ✅ Good: Use rate limiter
limiter = SimpleRateLimiter(calls_per_minute=60)

async def safe_generate(prompt):
    await limiter.acquire()
    return await router.generate(prompt)

# Prevents RateLimitError
```

### 5. Handle критичні помилки

```python
from src.core.ai.errors import FallbackFailedError

try:
    result = await router.generate(prompt)
    
except FallbackFailedError as e:
    # ✅ Good: Critical error handling
    logger.critical(f"All providers failed: {e}")
    
    # Send alert
    send_alert("Critical: AI service down", str(e))
    
    # Notify user
    return {
        "error": "AI service temporarily unavailable",
        "status": "degraded"
    }
```

### 6. Retry з exponential backoff

```python
import asyncio
from src.core.ai.errors import ProviderUnavailableError

async def generate_with_retry(prompt, max_retries=3):
    for attempt in range(max_retries):
        try:
            return await router.generate(prompt)
            
        except ProviderUnavailableError as e:
            if attempt == max_retries - 1:
                raise  # Last attempt failed
            
            # Exponential backoff
            wait_time = 2 ** attempt  # 1s, 2s, 4s
            logger.warning(f"Retry {attempt + 1}/{max_retries} after {wait_time}s")
            await asyncio.sleep(wait_time)
```

## 📊 Error Handling Examples

### Example 1: Agent with Error Handling

```python
from src.agents.summary_agent import SummaryAgent
from src.core.ai.router import AIProviderRouter
from src.core.ai.errors import FallbackFailedError, ProviderUnavailableError

async def generate_summary_safe(page_id: str):
    """Generate summary with comprehensive error handling"""
    
    router = AIProviderRouter(
        default_provider="openai",
        fallback_provider="gemini"
    )
    
    agent = SummaryAgent(ai_router=router, ai_provider="openai")
    
    try:
        # Try to generate
        summary = await agent.generate_summary(page_id)
        return {
            "status": "success",
            "summary": summary
        }
        
    except FallbackFailedError as e:
        # Critical: both providers failed
        logger.critical(f"All AI providers failed: {e}")
        send_alert("Critical: AI service down")
        
        return {
            "status": "error",
            "error": "AI service temporarily unavailable",
            "message": "Please try again later"
        }
        
    except ProviderUnavailableError as e:
        # Provider issue, maybe try cache
        logger.error(f"Provider unavailable: {e}")
        
        # Try cached summary
        cached = get_cached_summary(page_id)
        if cached:
            return {
                "status": "success",
                "summary": cached,
                "cached": True
            }
        
        return {
            "status": "error",
            "error": "AI provider unavailable",
            "message": "Please try again later"
        }
```

### Example 2: API Endpoint with Error Handling

```python
from fastapi import FastAPI, HTTPException
from src.core.ai.router import AIProviderRouter
from src.core.ai.errors import FallbackFailedError, ProviderUnavailableError

app = FastAPI()
router = AIProviderRouter()

@app.post("/api/generate")
async def generate_endpoint(prompt: str):
    """Generate text with error handling"""
    
    try:
        result = await router.generate(prompt)
        
        return {
            "status": "success",
            "text": result.text,
            "provider": result.provider,
            "tokens": result.total_tokens
        }
        
    except FallbackFailedError as e:
        # 503 Service Unavailable
        logger.critical(f"All providers failed: {e}")
        raise HTTPException(
            status_code=503,
            detail="AI service temporarily unavailable"
        )
        
    except ProviderUnavailableError as e:
        # 502 Bad Gateway
        logger.error(f"Provider unavailable: {e}")
        raise HTTPException(
            status_code=502,
            detail="AI provider unavailable"
        )
```

### Example 3: Batch Processing with Error Handling

```python
from src.core.ai.router import AIProviderRouter
from src.core.ai.errors import FallbackFailedError

async def batch_generate(prompts: list[str]):
    """Process batch with error handling"""
    
    router = AIProviderRouter()
    results = []
    errors = []
    
    for i, prompt in enumerate(prompts):
        try:
            result = await router.generate(prompt)
            results.append({
                "index": i,
                "status": "success",
                "text": result.text
            })
            
        except FallbackFailedError as e:
            # Log but continue processing
            logger.error(f"Item {i} failed: {e}")
            errors.append({
                "index": i,
                "error": str(e)
            })
        
        except Exception as e:
            # Unexpected error
            logger.error(f"Unexpected error for item {i}: {e}")
            errors.append({
                "index": i,
                "error": f"Unexpected: {e}"
            })
    
    return {
        "total": len(prompts),
        "successful": len(results),
        "failed": len(errors),
        "results": results,
        "errors": errors
    }
```

## 🧪 Testing

### Unit Tests

```bash
pytest tests/core/ai/test_errors_in_router.py -v
```

**12 тестів:**
- ✅ ProviderUnavailableError (3 tests)
  - Unknown provider
  - Primary fails, no fallback
  - Fallback same as primary
- ✅ Fallback success (2 tests)
  - Primary fails, fallback succeeds
  - Explicit provider with fallback
- ✅ FallbackFailedError (2 tests)
  - Both providers fail
  - Error details preserved
- ✅ Successful generation (1 test)
  - Primary succeeds, no fallback needed
- ✅ Error inheritance (2 tests)
  - All inherit from base
  - Can catch with base exception
- ✅ Error messages (2 tests)
  - Provider name in message
  - Both providers in fallback error

### Integration Test

```python
@pytest.mark.asyncio
async def test_full_error_flow():
    """Test complete error handling flow"""
    
    from src.core.ai.router import AIProviderRouter
    from src.core.ai.errors import FallbackFailedError
    
    router = AIProviderRouter()
    
    try:
        result = await router.generate("Test prompt")
        assert result.text  # Should have text
        
    except FallbackFailedError:
        # Both providers failed
        pytest.fail("Both providers failed in integration test")
```

## ✅ Переваги Error Handling Layer

1. ✅ **Type Safety** — typed exceptions для кращої обробки
2. ✅ **Clarity** — зрозуміло що пішло не так
3. ✅ **Predictability** — передбачувана поведінка
4. ✅ **Fallback** — автоматичне переключення на fallback
5. ✅ **Debugging** — детальна інформація про помилки
6. ✅ **Monitoring** — легко логувати та моніторити
7. ✅ **Graceful** — graceful degradation при збоях
8. ✅ **Production Ready** — готово для production

## 🚀 Готово до використання!

Error Handling Layer забезпечує надійну та передбачувану обробку помилок у вашій Multi-AI архітектурі!
