# Multi-AI Architecture

## 🎯 Цілі проєкту

Розширити Confluence_AI для підтримки кількох AI-провайдерів, забезпечивши:
- Гнучкий вибір провайдера (OpenAI, Google Gemini, Anthropic Claude, тощо)
- Автоматичний fallback при недоступності одного з провайдерів
- Cost optimization через розподіл запитів
- A/B testing різних моделей
- Централізоване керування API keys та конфігурацією

---

## 📋 План робіт

### Етап 1: Архітектура та інтерфейси (Тиждень 1-2)
- [ ] Створити абстрактний `AIProviderInterface`
- [ ] Реалізувати `AIRouter` для вибору провайдера
- [ ] Додати `ProviderFactory` для створення екземплярів
- [ ] Розробити систему fallback та retry логіки
- [ ] Оновити `.env` конфігурацію для multi-AI

### Етап 2: Реалізація провайдерів (Тиждень 3-4)
- [ ] **OpenAI Provider** (ChatGPT-4o, GPT-4o-mini)
  - Існуюча реалізація → рефакторинг під новий інтерфейс
- [ ] **Google Gemini Provider** (Gemini 1.5 Pro, Flash)
  - Інтеграція з `google-generativeai`
- [ ] **Anthropic Claude Provider** (опціонально)
  - Інтеграція з Claude API

### Етап 3: Конфігурація та маршрутизація (Тиждень 5)
- [ ] Provider selection strategy:
  - Manual (через `.env` або API параметр)
  - Round-robin (балансування навантаження)
  - Cost-based (вибір найдешевшого)
  - Performance-based (найшвидший response time)
- [ ] Система пріоритетів та fallback rules
- [ ] Monitoring та logging для кожного провайдера

### Етап 4: Тестування (Тиждень 6)
- [ ] Unit tests для кожного провайдера
- [ ] Integration tests з fallback логікою
- [ ] Performance benchmarks
- [ ] Cost comparison аналіз
- [ ] Documentation та migration guide

---

## 🏗️ Архітектурна діаграма

```
┌─────────────────────────────────────────────────┐
│           Confluence_AI Application             │
└─────────────────────┬───────────────────────────┘
                      │
                      ▼
          ┌───────────────────────┐
          │      AI Router        │
          │  (Provider Selection) │
          └───────────┬───────────┘
                      │
        ┌─────────────┼─────────────┐
        ▼             ▼             ▼
┌───────────┐  ┌───────────┐  ┌───────────┐
│  OpenAI   │  │  Gemini   │  │  Claude   │
│ Provider  │  │ Provider  │  │ Provider  │
└─────┬─────┘  └─────┬─────┘  └─────┬─────┘
      │              │              │
      ▼              ▼              ▼
   GPT-4o      Gemini 1.5     Claude 3.5
```

---

## 🔌 AI Провайдери

### 1. **OpenAI** (Поточний)
**Моделі:**
- `gpt-4o` — найпотужніша модель (128K context)
- `gpt-4o-mini` — швидка та економна версія
- `gpt-4-turbo` — попередня флагманська модель

**Переваги:**
- ✅ Вже інтегровано
- ✅ Стабільний API
- ✅ Відмінна якість для складних задач

**Недоліки:**
- ❌ Висока вартість для GPT-4o
- ❌ Rate limits при великих обсягах

**Використання:**
- Summary generation (high quality needed)
- Complex tagging scenarios
- Content rewriting

---

### 2. **Google Gemini** (Новий)
**Моделі:**
- `gemini-1.5-pro` — 1M context window, multimodal
- `gemini-1.5-flash` — швидка версія, 1M context
- `gemini-2.0-flash-exp` — experimental, найшвидша

**Переваги:**
- ✅ Величезний context window (1M tokens)
- ✅ Multimodal (текст + зображення)
- ✅ Безкоштовний tier (60 RPM)
- ✅ Низька вартість

**Недоліки:**
- ❌ Менш стабільний для structured output
- ❌ Нова інтеграція (потрібне тестування)

**Використання:**
- Large document processing (завдяки 1M context)
- Bulk operations (низька вартість)
- Image analysis (майбутнє розширення)

**API Integration:**
```python
import google.generativeai as genai

genai.configure(api_key=os.environ["GEMINI_API_KEY"])
model = genai.GenerativeModel("gemini-1.5-flash")
response = model.generate_content("Your prompt here")
```

---

### 3. **Anthropic Claude** (Опціонально)
**Моделі:**
- `claude-3-opus` — найпотужніша
- `claude-3-sonnet` — баланс
- `claude-3-haiku` — найшвидша

**Переваги:**
- ✅ Відмінна якість reasoning
- ✅ Безпечність (конституційний AI)
- ✅ 200K context

**Недоліки:**
- ❌ Вартість вища за Gemini
- ❌ Менше ecosystem tools

**Використання:**
- Critical decision-making
- Safety-sensitive operations

---

## ⚙️ Конфігурація

### `.env` структура (нова):
```bash
###############################################
# AI PROVIDERS CONFIGURATION
###############################################

# Global settings
DEFAULT_AI_PROVIDER=openai  # openai | gemini | claude
FALLBACK_ENABLED=true
FALLBACK_ORDER=openai,gemini,claude

# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
OPENAI_MAX_TOKENS=4000
OPENAI_TEMPERATURE=0.7

# Google Gemini
GEMINI_API_KEY=AIza...
GEMINI_MODEL=gemini-1.5-flash
GEMINI_MAX_TOKENS=8000
GEMINI_TEMPERATURE=0.7

# Anthropic Claude (optional)
CLAUDE_API_KEY=sk-ant-...
CLAUDE_MODEL=claude-3-haiku
CLAUDE_MAX_TOKENS=4000
```

### Per-agent провайдер (override):
```bash
# SummaryAgent → використовує OpenAI (якість)
SUMMARY_AGENT_PROVIDER=openai

# TaggingAgent → використовує Gemini (швидкість + вартість)
TAGGING_AGENT_PROVIDER=gemini

# ClassificationAgent → використовує Gemini (bulk операції)
CLASSIFICATION_AGENT_PROVIDER=gemini
```

---

## 🔄 Fallback стратегія

**Scenario 1: Primary Provider Down**
```
Request → OpenAI (❌ timeout)
       → Gemini (✅ success)
       → Return result
```

**Scenario 2: Rate Limit Hit**
```
Request → OpenAI (❌ 429 Too Many Requests)
       → Gemini (✅ success)
       → Return result + log switch
```

**Scenario 3: All Providers Down**
```
Request → OpenAI (❌)
       → Gemini (❌)
       → Claude (❌)
       → Return error + alert
```

---

## 📊 Cost Comparison

| Provider | Model | Input (1M tokens) | Output (1M tokens) | Context |
|----------|-------|-------------------|-------------------|---------|
| OpenAI | GPT-4o | $2.50 | $10.00 | 128K |
| OpenAI | GPT-4o-mini | $0.15 | $0.60 | 128K |
| Gemini | 1.5 Pro | $1.25 | $5.00 | 1M |
| Gemini | 1.5 Flash | $0.075 | $0.30 | 1M |
| Claude | Opus | $15.00 | $75.00 | 200K |
| Claude | Haiku | $0.25 | $1.25 | 200K |

**Висновок:** Gemini Flash — найдешевший для bulk операцій!

---

## 🧪 Testing Plan

### Unit Tests
- ✅ Кожен провайдер окремо
- ✅ Factory pattern створення
- ✅ Router selection logic

### Integration Tests
- ✅ Fallback scenarios
- ✅ Multi-provider requests
- ✅ Cost tracking

### Performance Tests
- ✅ Response time comparison
- ✅ Throughput benchmarks
- ✅ Context window limits

---

## 📚 Технічні деталі

### AIProviderInterface
```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class AIProviderInterface(ABC):
    """Base interface for all AI providers"""
    
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        max_tokens: int = 4000,
        temperature: float = 0.7,
        **kwargs
    ) -> str:
        """Generate text completion"""
        pass
    
    @abstractmethod
    def get_provider_name(self) -> str:
        """Return provider name (openai, gemini, claude)"""
        pass
    
    @abstractmethod
    def get_cost_per_token(self) -> Dict[str, float]:
        """Return cost per 1K tokens (input/output)"""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if provider is available"""
        pass
```

### AIRouter
```python
class AIRouter:
    """Routes requests to appropriate AI provider"""
    
    def __init__(self):
        self.providers = {}
        self.fallback_order = []
        self.default_provider = None
    
    def register_provider(self, name: str, provider: AIProviderInterface):
        """Register new provider"""
        self.providers[name] = provider
    
    async def generate(
        self,
        prompt: str,
        provider: Optional[str] = None,
        **kwargs
    ) -> tuple[str, str]:
        """
        Generate with specified or default provider.
        Returns (result, used_provider_name)
        """
        # Selection logic
        # Fallback logic
        # Error handling
        pass
```

---

## 🚀 Майбутні розширення

1. **Custom AI Endpoints**
   - Self-hosted LLMs (Llama, Mistral)
   - Azure OpenAI
   - AWS Bedrock

2. **Advanced Features**
   - Model ensembling (multiple providers vote)
   - Smart caching (reduce API calls)
   - Cost budgeting (daily/monthly limits)

3. **Monitoring Dashboard**
   - Real-time provider status
   - Cost analytics
   - Performance metrics

---

## 📝 Migration Guide

### Для існуючого коду:
```python
# Старий код (OpenAI only)
from openai import OpenAI
client = OpenAI()
response = client.chat.completions.create(...)

# Новий код (Multi-AI)
from src.ai.router import AIRouter
router = AIRouter()
response = await router.generate(
    prompt="...",
    provider="gemini"  # або None для default
)
```

---

**Статус:** 🟡 Planning  
**Дата початку:** 2025-12-30  
**Очікуване завершення:** 2026-02-10 (6 тижнів)

---

## 🤝 Contributing

Ця документація буде оновлюватися в процесі розробки.  
Всі рішення та зміни будуть документовані у `CHANGELOG.md`.
