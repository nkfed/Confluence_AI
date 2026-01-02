# AI Unified Logging Layer Documentation

## 📋 Огляд

**Unified Logging Layer** — це централізована система логування для всіх AI викликів, яка забезпечує повну прозорість операцій з AI провайдерами.

**Ключові можливості:**
- ✅ Автоматичне логування всіх AI викликів
- ✅ Єдиний формат для OpenAI і Gemini
- ✅ Інтеграція з cost tracking
- ✅ Вимірювання часу виконання
- ✅ Відстеження токенів
- ✅ Логування помилок
- ✅ Ізоляція від бізнес-логіки

## 🎯 Навіщо потрібен Unified Logging?

### Проблема: Розпорошене логування

```python
# Різне логування в різних місцях
# SummaryAgent
logger.info("OpenAI called")
result = await openai.generate(prompt)
logger.info(f"Tokens: {result.tokens}")

# TaggingAgent  
logger.debug("Calling Gemini")
result = await gemini.generate(prompt)
# Забули залогувати токени та вартість!
```

### Рішення: Єдиний Logging Wrapper

```python
from src.core.ai.logging_utils import log_ai_call

# SummaryAgent
result = await log_ai_call(
    provider_name="openai",
    model="gpt-4o-mini",
    operation="summary",
    coro=lambda: provider.generate(prompt)
)
# ✅ Автоматично логує: provider, model, duration, tokens, cost

# TaggingAgent
result = await log_ai_call(
    provider_name="gemini",
    model="gemini-2.0-flash-exp",
    operation="tagging",
    coro=lambda: provider.generate(prompt)
)
# ✅ Той самий формат логування!
```

## 🔧 Функція `log_ai_call()`

### Signature

```python
async def log_ai_call(
    provider_name: str,
    model: Optional[str],
    operation: str,
    coro: Callable[[], Awaitable[Any]],
) -> Any:
    """
    Universal logging wrapper for AI provider calls.
    
    Args:
        provider_name: Name of AI provider ('openai', 'gemini')
        model: Model name (e.g., 'gpt-4o-mini')
        operation: Operation type ('summary', 'tagging', etc.)
        coro: Async callable that performs the AI operation
        
    Returns:
        Result from the AI operation
    """
```

### Що логується

#### На успіх:
```python
INFO AI call succeeded
  provider: openai
  model: gpt-4o-mini
  operation: summary
  duration_sec: 0.4235
  prompt_tokens: 1200
  completion_tokens: 300
  total_tokens: 1500
  cost_usd: 0.00036
```

#### На помилку:
```python
ERROR AI call failed
  provider: openai
  model: gpt-4o-mini
  operation: summary
  duration_sec: 0.1523
  error: Rate limit exceeded
  error_type: RateLimitError
```

## 🚀 Використання

### 1. Basic Usage

```python
from src.core.ai.logging_utils import log_ai_call

# Wrap any AI call
result = await log_ai_call(
    provider_name="openai",
    model="gpt-4o-mini",
    operation="summary",
    coro=lambda: client.generate(prompt)
)

# Result is unchanged, logging is automatic
print(result.text)
```

### 2. In SummaryAgent

```python
from src.agents.summary_agent import SummaryAgent
from src.core.ai.router import AIProviderRouter

# Agent automatically uses unified logging
router = AIProviderRouter()
agent = SummaryAgent(ai_router=router, ai_provider="openai")

# All AI calls are logged automatically
summary = await agent.generate_summary(page_id="12345")

# Logs:
# INFO AI call succeeded provider=openai model=gpt-4o-mini operation=summary
#      duration_sec=0.42 prompt_tokens=800 completion_tokens=150 total_tokens=950
#      cost_usd=0.000210
```

### 3. In TaggingAgent

```python
from src.agents.tagging_agent import TaggingAgent
from src.core.ai.router import AIProviderRouter

# Agent automatically uses unified logging
router = AIProviderRouter()
agent = TaggingAgent(ai_router=router, ai_provider="gemini")

# All AI calls are logged automatically
tags = await agent.suggest_tags("Content to tag")

# Logs:
# INFO AI call succeeded provider=gemini model=gemini-2.0-flash-exp operation=tagging
#      duration_sec=0.28 prompt_tokens=300 completion_tokens=50 total_tokens=350
#      cost_usd=0.000038
```

### 4. Custom Operations

```python
from src.core.ai.logging_utils import log_ai_call

# Any custom AI operation
result = await log_ai_call(
    provider_name="openai",
    model="gpt-4o-mini",
    operation="translation",
    coro=lambda: client.generate("Translate to Ukrainian: Hello")
)

result = await log_ai_call(
    provider_name="gemini",
    model="gemini-2.0-flash-exp",
    operation="classification",
    coro=lambda: client.generate("Classify: This is a technical document")
)
```

## 📊 Log Format Examples

### Success Log (Full)

```
2025-12-30 19:15:42 | INFO | src.core.ai.logging_utils | - | AI call succeeded
{
  "provider": "openai",
  "model": "gpt-4o-mini",
  "operation": "summary",
  "duration_sec": 0.4235,
  "prompt_tokens": 1200,
  "completion_tokens": 300,
  "total_tokens": 1500,
  "cost_usd": 0.00036
}
```

### Success Log (Without Tokens)

```
2025-12-30 19:16:10 | INFO | src.core.ai.logging_utils | - | AI call succeeded
{
  "provider": "gemini",
  "model": "gemini-2.0-flash-exp",
  "operation": "count_tokens",
  "duration_sec": 0.0523,
  "cost_usd": null
}
```

### Error Log

```
2025-12-30 19:16:45 | ERROR | src.core.ai.logging_utils | - | AI call failed
{
  "provider": "openai",
  "model": "gpt-4o-mini",
  "operation": "summary",
  "duration_sec": 0.1523,
  "error": "Rate limit exceeded for requests",
  "error_type": "RateLimitError"
}
```

## 💡 Use Cases

### Use Case 1: Production Monitoring

```python
# All AI calls are automatically logged
# Parse logs to build dashboards

# Example log analysis:
# - Total AI calls: 1,523
# - Average duration: 0.42s
# - Total tokens: 2,450,000
# - Total cost: $0.87
# - Error rate: 0.3%
```

### Use Case 2: Performance Tuning

```python
# Compare performance across providers

# OpenAI logs:
# - Average duration: 0.45s
# - Average cost: $0.00045

# Gemini logs:
# - Average duration: 0.32s
# - Average cost: $0.00022

# Conclusion: Gemini is faster and cheaper for tagging
```

### Use Case 3: Cost Analysis

```python
# Aggregate costs by operation

# From logs:
# - summary operations: 500 calls, $0.45 total
# - tagging operations: 1000 calls, $0.22 total

# Insights:
# - Summary is more expensive per call
# - Tagging has higher volume
# - Total: $0.67
```

### Use Case 4: Audit Trail

```python
# Full audit trail of all AI operations

# Example:
# 2025-12-30 14:00:00 - User X requested summary for page 12345
# 2025-12-30 14:00:01 - OpenAI called (0.42s, $0.00036)
# 2025-12-30 14:00:02 - Summary generated successfully
```

### Use Case 5: Debugging

```python
# When errors occur, full context is logged

# Error log shows:
# - Which provider failed
# - Which model was used
# - What operation was attempted
# - How long it took to fail
# - Exact error message

# Makes debugging much easier!
```

## 🎯 Integration Details

### How It Works

```python
# 1. Agent calls log_ai_call
result = await log_ai_call(
    provider_name="openai",
    model="gpt-4o-mini",
    operation="summary",
    coro=lambda: provider.generate(prompt)
)

# 2. log_ai_call measures start time
start = time.time()

# 3. Executes the AI operation
result = await coro()

# 4. Calculates duration
duration = time.time() - start

# 5. Extracts token info (if available)
tokens = {
    "prompt_tokens": result.prompt_tokens,
    "completion_tokens": result.completion_tokens,
    "total_tokens": result.total_tokens
}

# 6. Calculates cost estimate
cost = calculator.estimate(provider, tokens)

# 7. Logs everything
logger.info("AI call succeeded", extra={...})

# 8. Returns original result
return result
```

### Integration Points

**SummaryAgent:**
```python
# Before
ai_response = await provider.generate(prompt)

# After
ai_response = await log_ai_call(
    provider_name=provider.name,
    model=provider.model_default,
    operation="summary",
    coro=lambda: provider.generate(prompt)
)
```

**TaggingAgent:**
```python
# Before
ai_response = await provider.generate(prompt)

# After
ai_response = await log_ai_call(
    provider_name=provider.name,
    model=provider.model_default,
    operation="tagging",
    coro=lambda: provider.generate(prompt)
)
```

## 📈 Log Analysis Examples

### Example 1: Daily Report

```bash
# Parse logs for daily summary
grep "AI call succeeded" app.log | \
  jq -s '{
    total_calls: length,
    total_tokens: map(.total_tokens) | add,
    total_cost: map(.cost_usd) | add,
    avg_duration: (map(.duration_sec) | add / length)
  }'
```

**Output:**
```json
{
  "total_calls": 1523,
  "total_tokens": 2450000,
  "total_cost": 0.87,
  "avg_duration": 0.42
}
```

### Example 2: Provider Comparison

```python
# Group by provider
import json

openai_calls = []
gemini_calls = []

with open('app.log') as f:
    for line in f:
        if 'AI call succeeded' in line:
            data = json.loads(line.split('|')[-1])
            if data['provider'] == 'openai':
                openai_calls.append(data)
            elif data['provider'] == 'gemini':
                gemini_calls.append(data)

print(f"OpenAI: {len(openai_calls)} calls, ${sum(c['cost_usd'] for c in openai_calls):.2f}")
print(f"Gemini: {len(gemini_calls)} calls, ${sum(c['cost_usd'] for c in gemini_calls):.2f}")
```

### Example 3: Operation Breakdown

```python
# Group by operation
from collections import defaultdict

operations = defaultdict(lambda: {'count': 0, 'cost': 0, 'duration': 0})

with open('app.log') as f:
    for line in f:
        if 'AI call succeeded' in line:
            data = json.loads(line.split('|')[-1])
            op = data['operation']
            operations[op]['count'] += 1
            operations[op]['cost'] += data['cost_usd']
            operations[op]['duration'] += data['duration_sec']

for op, stats in operations.items():
    avg_duration = stats['duration'] / stats['count']
    print(f"{op}: {stats['count']} calls, ${stats['cost']:.2f}, {avg_duration:.2f}s avg")
```

## 🧪 Testing

### Unit Tests

```bash
pytest tests/core/ai/test_logging_utils.py -v
```

**13 тестів:**
- ✅ Success logging (7 tests)
  - Executes coro
  - Logs success
  - Includes provider and model
  - Includes duration
  - Includes tokens
  - Includes cost
- ✅ Error logging (4 tests)
  - Logs error
  - Includes error type
  - Re-raises exception
  - Includes duration on error
- ✅ Without tokens (1 test)
  - Handles missing tokens gracefully
- ✅ Integration (2 tests)
  - SummaryAgent uses log_ai_call
  - TaggingAgent uses log_ai_call

### Integration Test

```python
import pytest
from src.agents.summary_agent import SummaryAgent
from src.core.ai.router import AIProviderRouter

@pytest.mark.asyncio
async def test_full_logging_flow():
    """Test complete logging flow with real agents"""
    
    router = AIProviderRouter()
    agent = SummaryAgent(ai_router=router, ai_provider="openai")
    
    # This will trigger unified logging
    summary = await agent.generate_summary("12345")
    
    # Check logs (in production, parse log files)
    # Should see: AI call succeeded with full details
```

## 🎯 Best Practices

### 1. Always Use log_ai_call

```python
# ✅ Good: Unified logging
result = await log_ai_call(
    provider_name="openai",
    model="gpt-4o-mini",
    operation="summary",
    coro=lambda: client.generate(prompt)
)

# ❌ Bad: Manual logging
logger.info("Calling OpenAI")
result = await client.generate(prompt)
logger.info(f"Done, tokens: {result.total_tokens}")
```

### 2. Use Descriptive Operations

```python
# ✅ Good: Clear operation names
operation="summary"
operation="tagging"
operation="translation"
operation="classification"

# ❌ Bad: Generic names
operation="generate"
operation="call"
operation="ai"
```

### 3. Parse Logs Regularly

```python
# Build automated log analysis
# - Daily cost reports
# - Performance dashboards
# - Error alerts
```

### 4. Set Up Alerts

```python
# Alert on high error rates
if error_rate > 5%:
    send_alert("High AI error rate!")

# Alert on high costs
if daily_cost > budget:
    send_alert("AI budget exceeded!")
```

## ✅ Переваги Unified Logging

1. ✅ **Consistency** — єдиний формат для всіх провайдерів
2. ✅ **Transparency** — повна видимість AI викликів
3. ✅ **Cost Tracking** — автоматичний розрахунок вартості
4. ✅ **Performance** — вимірювання часу виконання
5. ✅ **Debugging** — детальне логування помилок
6. ✅ **Monitoring** — готово для production dashboards
7. ✅ **Audit Trail** — повний аудит всіх операцій
8. ✅ **Isolation** — не залежить від бізнес-логіки

## 🚀 Готово до використання!

Unified Logging Layer забезпечує повну прозорість та контроль над усіма AI викликами у вашому додатку!
