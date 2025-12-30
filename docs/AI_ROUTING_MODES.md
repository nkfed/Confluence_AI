# AI Routing Modes Documentation

## 📋 Огляд

AI Provider Router підтримує **4 режими маршрутизації** для гнучкого керування AI провайдерами (OpenAI, Gemini).

Режим визначає, який провайдер використовується основним і який як fallback.

## 🎯 Режими маршрутизації

### Mode A: Quality First (OpenAI → Gemini)

**Конфігурація:**
```env
AI_ROUTING_MODE=A
```

**Поведінка:**
- **Primary:** OpenAI
- **Fallback:** Gemini

**Use Cases:**
- ✅ Критичні продакшн застосунки
- ✅ Високі вимоги до якості
- ✅ Складні задачі (аналіз, summarization)
- ✅ Коли точність важливіша за вартість

**Приклад:**
```python
from src.core.config.ai_settings import settings

# Mode A активований
primary, fallback = settings.get_router_config()
# → ("openai", "gemini")
```

---

### Mode B: Cost First (Gemini → OpenAI)

**Конфігурація:**
```env
AI_ROUTING_MODE=B
```

**Поведінка:**
- **Primary:** Gemini
- **Fallback:** OpenAI

**Use Cases:**
- ✅ Bulk операції (тисячі сторінок)
- ✅ Оптимізація витрат
- ✅ Швидкі, прості задачі
- ✅ Тестування, development

**Приклад:**
```python
# Mode B: дешевше для масових операцій
router = AIProviderRouter(
    default_provider="gemini",
    fallback_provider="openai"
)

# Обробка тисяч сторінок
for page in large_batch:
    tags = await tagging_agent.suggest_tags(text)  # Uses Gemini
```

---

### Mode C: Balanced (Custom per Agent)

**Конфігурація:**
```env
AI_ROUTING_MODE=C
DEFAULT_AI_PROVIDER=openai
FALLBACK_AI_PROVIDER=gemini
```

**Поведінка:**
- **Primary:** Визначається `DEFAULT_AI_PROVIDER`
- **Fallback:** Визначається `FALLBACK_AI_PROVIDER`

**Use Cases:**
- ✅ Різні провайдери для різних агентів
- ✅ SummaryAgent → OpenAI (якість)
- ✅ TaggingAgent → Gemini (швидкість)
- ✅ Баланс між якістю та вартістю

**Приклад:**
```python
# Custom routing per agent
router = AIProviderRouter()  # Uses settings

# SummaryAgent uses OpenAI (quality)
summary_agent = SummaryAgent(
    ai_router=router,
    ai_provider="openai"
)

# TaggingAgent uses Gemini (speed/cost)
tagging_agent = TaggingAgent(
    ai_router=router,
    ai_provider="gemini"
)
```

---

### Mode D: A/B Testing

**Конфігурація:**
```env
AI_ROUTING_MODE=D
DEFAULT_AI_PROVIDER=openai  # Or gemini for comparison
```

**Поведінка:**
- **Primary:** Визначається `DEFAULT_AI_PROVIDER`
- **Fallback:** Визначається `FALLBACK_AI_PROVIDER`

**Use Cases:**
- ✅ Порівняння якості провайдерів
- ✅ Тестування нових моделей
- ✅ Вимірювання performance
- ✅ Вибір оптимального провайдера

**Приклад:**
```python
# Compare providers
from src.core.config.ai_settings import AISettings

# Test with OpenAI
settings_openai = AISettings(
    AI_ROUTING_MODE="D",
    DEFAULT_AI_PROVIDER="openai"
)
agent_openai = SummaryAgent(ai_router=router_openai)
result_openai = await agent_openai.generate_summary(page_id)

# Test with Gemini
settings_gemini = AISettings(
    AI_ROUTING_MODE="D",
    DEFAULT_AI_PROVIDER="gemini"
)
agent_gemini = SummaryAgent(ai_router=router_gemini)
result_gemini = await agent_gemini.generate_summary(page_id)

# Compare results
print(f"OpenAI: {len(result_openai)} chars")
print(f"Gemini: {len(result_gemini)} chars")
```

---

## 📊 Порівняльна таблиця

| Mode | Primary | Fallback | Use Case | Priority |
|------|---------|----------|----------|----------|
| **A** | OpenAI | Gemini | Production, Quality | Quality ⭐⭐⭐⭐⭐ |
| **B** | Gemini | OpenAI | Bulk ops, Cost saving | Cost ⭐⭐⭐⭐⭐ |
| **C** | Custom | Custom | Per-agent routing | Balance ⭐⭐⭐⭐ |
| **D** | Custom | Custom | A/B testing | Testing ⭐⭐⭐ |

---

## 🔧 Як змінити режим

### 1. Через .env файл (Рекомендовано)

```bash
# Відредагуйте .env
AI_ROUTING_MODE=B  # Змінити на потрібний режим
```

### 2. Через код

```python
from src.core.config.ai_settings import AISettings

# Create custom settings
settings = AISettings(AI_ROUTING_MODE="B")
primary, fallback = settings.get_router_config()
```

### 3. Через environment variable

```bash
# Windows
$env:AI_ROUTING_MODE="B"
python your_script.py

# Linux/Mac
export AI_ROUTING_MODE=B
python your_script.py
```

---

## 📈 Performance характеристики

### OpenAI (gpt-4o-mini)
- **Якість:** ⭐⭐⭐⭐⭐ (відмінна)
- **Швидкість:** ⭐⭐⭐⭐ (швидко)
- **Вартість:** $$$$ (дорого)
- **Context window:** 128K tokens

### Google Gemini (2.0-flash-exp)
- **Якість:** ⭐⭐⭐⭐ (дуже добре)
- **Швидкість:** ⭐⭐⭐⭐⭐ (дуже швидко)
- **Вартість:** $ (дешево)
- **Context window:** 1M tokens

---

## 🎯 Рекомендації вибору режиму

### Production (Продакшн)
```env
AI_ROUTING_MODE=A  # Quality first
```
✅ Надійність  
✅ Якість  
✅ OpenAI → Gemini fallback

### Development (Розробка)
```env
AI_ROUTING_MODE=B  # Cost first
```
✅ Економія коштів  
✅ Швидкість  
✅ Gemini → OpenAI fallback

### Bulk Operations (Масові операції)
```env
AI_ROUTING_MODE=B  # Cost optimization
```
✅ Низька вартість  
✅ Висока пропускна здатність  
✅ 1000+ сторінок

### Mixed Workload (Змішане навантаження)
```env
AI_ROUTING_MODE=C  # Per-agent routing
DEFAULT_AI_PROVIDER=openai
FALLBACK_AI_PROVIDER=gemini
```
✅ Гнучкість  
✅ Оптимізація за задачами  
✅ Баланс якості та вартості

---

## 🧪 Перевірка активного режиму

### Через код
```python
from src.core.config.ai_settings import settings

# Перевірити поточний режим
print(f"Routing Mode: {settings.AI_ROUTING_MODE}")
primary, fallback = settings.get_router_config()
print(f"Primary: {primary}, Fallback: {fallback}")

# Validate configuration
status = settings.validate_config()
print(f"OpenAI available: {status['openai_available']}")
print(f"Gemini available: {status['gemini_available']}")
if status['warnings']:
    print(f"Warnings: {status['warnings']}")
```

### Через CLI
```bash
# Windows PowerShell
python -c "from src.core.config.ai_settings import settings; print(settings.get_router_config())"

# Output: ('openai', 'gemini')  # For Mode A
```

---

## ⚙️ Налаштування провайдерів

### Повна конфігурація .env

```bash
# OpenAI Settings
OPENAI_API_KEY=sk-proj-...
OPENAI_MODEL=gpt-4o-mini

# Google Gemini Settings
GEMINI_API_KEY=AIzaSy...
GEMINI_MODEL=gemini-2.0-flash-exp

# Router Settings
DEFAULT_AI_PROVIDER=openai
FALLBACK_AI_PROVIDER=gemini
AI_ROUTING_MODE=A
```

### Підтримувані моделі

**OpenAI:**
- `gpt-4o` — найкраща якість
- `gpt-4o-mini` — баланс (рекомендовано)
- `gpt-3.5-turbo` — економія

**Gemini:**
- `gemini-2.0-flash-exp` — найшвидша (рекомендовано)
- `gemini-1.5-pro` — висока якість
- `gemini-1.5-flash` — баланс

---

## 🚨 Troubleshooting

### Проблема: Provider недоступний

**Симптоми:**
```
ValueError: AI provider 'openai' is not configured
```

**Рішення:**
1. Перевірте API ключі в `.env`
2. Перезапустіть додаток
3. Перевірте `settings.validate_config()`

### Проблема: Fallback не спрацьовує

**Причина:** Fallback спрацьовує тільки при помилках primary provider

**Рішення:**
```python
# Використовуйте router.generate() для автоматичного fallback
response = await router.generate(prompt)  # ✅ Fallback працює

# Не використовуйте прямий виклик provider
provider = router.get("openai")
response = await provider.generate(prompt)  # ❌ Fallback НЕ працює
```

### Проблема: Невірний режим

**Симптоми:**
```
Unexpected routing behavior
```

**Рішення:**
```python
# Перевірте активний режим
from src.core.config.ai_settings import settings
print(f"Mode: {settings.AI_ROUTING_MODE}")
print(f"Config: {settings.get_router_config()}")
```

---

## 📚 Приклади використання

### Приклад 1: Production Quality
```python
# .env: AI_ROUTING_MODE=A
from src.agents.summary_agent import SummaryAgent
from src.core.ai.router import AIProviderRouter
from src.core.config.ai_settings import settings

# Router reads from settings automatically
primary, fallback = settings.get_router_config()
router = AIProviderRouter(
    default_provider=primary,
    fallback_provider=fallback
)

agent = SummaryAgent(ai_router=router)
summary = await agent.generate_summary(page_id)
```

### Приклад 2: Cost Optimization
```python
# .env: AI_ROUTING_MODE=B
router = AIProviderRouter(
    default_provider="gemini",
    fallback_provider="openai"
)

# Process 1000+ pages cheaply
for page_id in bulk_pages:
    tags = await tagging_agent.suggest_tags(text)
```

### Приклад 3: Per-Agent Routing
```python
# .env: AI_ROUTING_MODE=C
router = AIProviderRouter()

# Quality for summaries
summary_agent = SummaryAgent(
    ai_router=router,
    ai_provider="openai"
)

# Speed for tagging
tagging_agent = TaggingAgent(
    ai_router=router,
    ai_provider="gemini"
)
```

---

## ✅ Best Practices

1. **Production** → Mode A (Quality First)
2. **Development** → Mode B (Cost First)
3. **Bulk Operations** → Mode B (Gemini primary)
4. **Always configure fallback** для надійності
5. **Monitor costs** через token tracking
6. **Test both providers** перед production
7. **Use validation** для перевірки конфігурації

---

## 🎉 Готово до використання!

Routing modes забезпечують максимальну гнучкість у виборі AI провайдерів для різних сценаріїв!
