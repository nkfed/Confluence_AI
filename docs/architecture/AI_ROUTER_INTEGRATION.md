# AI Router Integration with Agents

## 📋 Огляд

SummaryAgent та TaggingAgent тепер підтримують **AIProviderRouter** для гнучкого вибору AI провайдерів (OpenAI, Gemini, тощо) з автоматичним fallback.

## ✅ Що змінилося

### До (Legacy)
```python
from src.agents.summary_agent import SummaryAgent
from src.clients.openai_client import OpenAIClient

# Тільки OpenAI
agent = SummaryAgent(openai_client=OpenAIClient())
summary = await agent.generate_summary(page_id)
```

### Після (Multi-AI)
```python
from src.agents.summary_agent import SummaryAgent
from src.core.ai.router import AIProviderRouter

# Використання router з fallback
router = AIProviderRouter(
    default_provider="openai",
    fallback_provider="gemini"
)

agent = SummaryAgent(ai_router=router)
summary = await agent.generate_summary(page_id)
# Автоматично використовує OpenAI, fallback на Gemini при помилках
```

## 🔧 Способи використання

### 1. **З Router (Рекомендовано)**

#### Default Provider
```python
from src.core.ai.router import AIProviderRouter

router = AIProviderRouter()  # default: openai
agent = SummaryAgent(ai_router=router)
```

#### З Fallback
```python
router = AIProviderRouter(
    default_provider="openai",
    fallback_provider="gemini"
)

summary_agent = SummaryAgent(ai_router=router)
tagging_agent = TaggingAgent(ai_router=router)
```

#### З конкретним провайдером
```python
# Завжди використовувати Gemini
router = AIProviderRouter(default_provider="gemini")
agent = SummaryAgent(ai_router=router, ai_provider="gemini")
```

### 2. **Legacy Mode (Backward Compatible)**

```python
from src.clients.openai_client import OpenAIClient

# Старий спосіб все ще працює
agent = SummaryAgent(openai_client=OpenAIClient())
summary = await agent.generate_summary(page_id)
```

## 📝 Конфігурація через .env

```bash
# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini

# Gemini (Optional)
GEMINI_API_KEY=AIza...
GEMINI_MODEL=gemini-2.0-flash-exp

# Router Settings (Optional)
DEFAULT_AI_PROVIDER=openai
FALLBACK_AI_PROVIDER=gemini
```

## 🎯 Use Cases

### Use Case 1: Cost Optimization
```python
# Використовуйте Gemini для bulk операцій (дешевше)
router = AIProviderRouter(default_provider="gemini")
tagging_agent = TaggingAgent(ai_router=router)

# Масове тегування сотень сторінок
for page_id in large_page_list:
    tags = await tagging_agent.suggest_tags(text)
```

### Use Case 2: Fallback на випадок Rate Limits
```python
# OpenAI основний, Gemini як backup
router = AIProviderRouter(
    default_provider="openai",
    fallback_provider="gemini"
)

summary_agent = SummaryAgent(ai_router=router)

# Якщо OpenAI rate limit → автоматично Gemini
summary = await summary_agent.generate_summary(page_id)
```

### Use Case 3: A/B Testing
```python
# Порівняти якість різних моделей
router = AIProviderRouter()

# Test OpenAI
agent_openai = SummaryAgent(ai_router=router, ai_provider="openai")
summary_openai = await agent_openai.generate_summary(page_id)

# Test Gemini
agent_gemini = SummaryAgent(ai_router=router, ai_provider="gemini")
summary_gemini = await agent_gemini.generate_summary(page_id)

# Compare results
```

### Use Case 4: Quality vs Speed
```python
# OpenAI для складних задач (якість)
router_quality = AIProviderRouter(default_provider="openai")
summary_agent = SummaryAgent(ai_router=router_quality)

# Gemini для простих задач (швидкість)
router_fast = AIProviderRouter(default_provider="gemini")
tagging_agent = TaggingAgent(ai_router=router_fast)
```

## 🧪 Приклади тестів

### Test з Router
```python
import pytest
from src.agents.summary_agent import SummaryAgent
from src.core.ai.router import AIProviderRouter

@pytest.mark.asyncio
async def test_summary_with_router():
    router = AIProviderRouter()
    agent = SummaryAgent(ai_router=router)
    
    summary = await agent.generate_summary(page_id="123")
    assert summary is not None
```

### Test Backward Compatibility
```python
@pytest.mark.asyncio
async def test_legacy_openai_client():
    from src.clients.openai_client import OpenAIClient
    
    agent = SummaryAgent(openai_client=OpenAIClient())
    summary = await agent.generate_summary(page_id="123")
    
    assert summary is not None
```

## 📊 Порівняння провайдерів

| Feature | OpenAI | Gemini |
|---------|--------|--------|
| **Якість** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Швидкість** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Вартість** | $$$$ | $ |
| **Context** | 128K | 1M |
| **Use Case** | Складні задачі | Bulk операції |

## 🚀 Migration Guide

### Крок 1: Оновити імпорти
```python
# Додати
from src.core.ai.router import AIProviderRouter
```

### Крок 2: Створити Router
```python
# Глобальний router (один на весь додаток)
router = AIProviderRouter(
    default_provider="openai",
    fallback_provider="gemini"
)
```

### Крок 3: Передати Router в Agents
```python
# Замість
agent = SummaryAgent(openai_client=OpenAIClient())

# Використовувати
agent = SummaryAgent(ai_router=router)
```

### Крок 4: (Optional) Видалити старі клієнти
```python
# Можна видалити після повної міграції
# from src.clients.openai_client import OpenAIClient
```

## ⚡ Performance Tips

1. **Reuse Router** — створіть один router на весь додаток
2. **Choose Provider** — OpenAI для якості, Gemini для швидкості
3. **Enable Fallback** — завжди налаштовуйте fallback для продакшн
4. **Monitor Tokens** — відстежуйте `ai_response.total_tokens`

## 🔒 Security Notes

- API keys зберігайте в `.env`
- Не комітьте `.env` в git
- Використовуйте різні keys для dev/prod
- Rotating keys підтримується без перезапуску

## ✅ Переваги нової архітектури

1. ✅ **Гнучкість** — легко перемикати провайдерів
2. ✅ **Надійність** — автоматичний fallback
3. ✅ **Cost Optimization** — вибір найдешевшого
4. ✅ **A/B Testing** — порівняння моделей
5. ✅ **Backward Compatible** — старий код працює
6. ✅ **Extensible** — легко додати нові провайдери

## 🎉 Готово до використання!

Agents тепер підтримують multi-AI архітектуру з повною backward compatibility!
