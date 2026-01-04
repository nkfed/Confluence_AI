# ⚙️ ДОРОЖНА КАРТА ОПТИМІЗАЦІЇ AI PROVIDERS

## 🎯 Пріоритет 1: КРИТИЧНО (протягом 1-2 днів)

### 1.1 Перевірка Gemini API Quotas

**Статус:** ❌ НЕВІДОМО  
**Вплив:** КРИТИЧНИЙ — API повністю блокується при вичерпанні квоти

**Дії:**
```bash
# Крок 1: Відкрити Google Cloud Console
https://console.cloud.google.com/

# Крок 2: Перейти в APIs & Services → Quotas
# Шукати: "Generative Language API"

# Крок 3: Перевірити поточні квоти
- Requests per minute per user (RPM)
- Tokens per minute per project (TPM)
- Concurrent requests

# Крок 4: Переглянути Usage
- Звіт за останні 24 години
- Ймовірна причина: Free tier має обмежені квоти

# Крок 5: Якщо квота обмежена
  Option A: Upgrade на Paid tier ($300+ за місяць)
  Option B: Розподілити запити в часі (queuing)
  Option C: Альтернативна модель (Claude, Mistral)
```

**Очікуваний результат:** Gemini стане стабільним, без 429 помилок

---

### 1.2 Реалізувати Exponential Backoff

**Файл для редакції:** `src/core/ai/gemini_client.py`

**Поточний код (~line 140-200):**
```python
async def generate(self, prompt: str, **kwargs) -> AIResponse:
    for attempt in range(max_retries):  # max_retries = 2
        try:
            response = self.client.models.generate_content(prompt)
            return parse_response(response)
        except HTTPStatusError as e:
            if e.status_code == 429:
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)  # ← лінійна затримка!
                else:
                    raise RuntimeError(f"Rate limit after {max_retries} attempts")
```

**Рекомендована зміна:**
```python
async def generate(self, prompt: str, **kwargs) -> AIResponse:
    max_retries = 4  # Збільшити з 2
    base_wait = 2  # Стартова затримка
    
    for attempt in range(max_retries):
        try:
            response = self.client.models.generate_content(prompt)
            return parse_response(response)
        except HTTPStatusError as e:
            if e.status_code == 429:
                if attempt < max_retries - 1:
                    # Exponential backoff: 2s → 4s → 8s → 16s
                    wait_time = min(base_wait * (2 ** attempt), 16)
                    logger.warning(f"Rate limit, waiting {wait_time}s before retry {attempt+1}/{max_retries}")
                    await asyncio.sleep(wait_time)
                else:
                    raise RuntimeError(f"Rate limit after {max_retries} attempts")
```

**Очікуваний результат:** Більше шансів на успіх при тимчасових лімітах

---

## 🎯 Пріоритет 2: ВАЖЛИВО (протягом тижня)

### 2.1 Реалізувати Client-side Rate Limiting

**Файл для створення:** `src/core/ai/rate_limiter.py`

```python
import asyncio
from collections import deque
from datetime import datetime
from typing import Callable

class RateLimiter:
    def __init__(self, max_requests_per_minute: int = 60, provider: str = "gemini"):
        self.max_requests = max_requests_per_minute
        self.provider = provider
        self.request_times = deque()
        self.lock = asyncio.Lock()
    
    async def wait_if_needed(self):
        """Затримайте запит, якщо наближаємося до ліміту"""
        async with self.lock:
            now = datetime.now()
            
            # Видалити запити старші за 60 секунд
            while self.request_times and (now - self.request_times[0]).total_seconds() > 60:
                self.request_times.popleft()
            
            # Якщо досягли ліміту, чекаємо
            if len(self.request_times) >= self.max_requests:
                wait_time = 60 - (now - self.request_times[0]).total_seconds()
                logger.warning(
                    f"[{self.provider}] Rate limit approaching. "
                    f"Waiting {wait_time:.1f}s before next request"
                )
                await asyncio.sleep(max(0.1, wait_time))
            
            self.request_times.append(datetime.now())
    
    def get_current_rate(self) -> float:
        """Повернути поточну частоту запитів на хвилину"""
        now = datetime.now()
        # Видалити старі запити
        while self.request_times and (now - self.request_times[0]).total_seconds() > 60:
            self.request_times.popleft()
        return len(self.request_times)

# Глобальні rate limiters
GEMINI_LIMITER = RateLimiter(max_requests_per_minute=40, provider="gemini")  # Консервативно
OPENAI_LIMITER = RateLimiter(max_requests_per_minute=60, provider="openai")
```

**Інтеграція з GeminiClient:**
```python
class GeminiClient:
    def __init__(self, api_key: str, model: str = "gemini-2.0-flash-exp"):
        self.api_key = api_key
        self.model = model
        self.rate_limiter = GEMINI_LIMITER
    
    async def generate(self, prompt: str, **kwargs) -> AIResponse:
        # Чекати, якщо потрібно
        await self.rate_limiter.wait_if_needed()
        
        # Решта логіки...
```

**Очікуваний результат:** Запити розподілені рівномірно, менше 429 помилок

---

### 2.2 Оптимізація Prompt для Gemini

**Поточна ситуація:**
- Prompt для tagging: **4465 tokens** (дуже велико)
- Gemini має обмежену контекстну вікно за вартістю

**Дії:**

1. **Скоротити system prompt:**
```python
# Поточна версія (дуже деталізована):
TAGGING_PROMPT = """
Ти — класифікаційний агент для Confluence.
Твоє завдання — проаналізувати текст...
[20+ рядків інструкцій]
Правила: [детальний список]
...
"""

# Оптимізована версія:
TAGGING_PROMPT_OPTIMIZED = """
Classify Confluence page text using provided tags only.
Return JSON: {"doc": [], "domain": [], "kb": [], "tool": []}
Max 3 tags per category. Use only if explicitly mentioned.
"""
# ← 5 рядків вместо 20+, економія ~300 tokens
```

2. **Скоротити приклади:**
```python
# Замість 10+ прикладів
EXAMPLES = [
    # Top 3 high-quality examples only
]
```

3. **Додати мемоізацію для instruction tokens:**
```python
# Gemini підтримує request caching
# Якщо system prompt однаковий, він кешується

cached_prompt = """@cached
You are a tagging agent...
"""  # ← Gemini запам'ятає ці токени, не буде повторно рахувати
```

**Очікуваний результат:** Скорочення prompt з 4465 на ~2000-2500 tokens = більше свободи для контенту

---

### 2.3 Налаштування Gemini параметрів

**Файл для редакції:** `.env`

```env
# ЖМАРКИЙ ПАРАМЕТРИ ДЛЯ TAGGING

# Вже добре:
GEMINI_MODEL=gemini-2.0-flash-exp  # ✅ швидка, дешева

# ПОТРЕБУЄ ЗМІНИ:
GEMINI_TEMPERATURE=0.7             # → 0.2 (для стабільної JSON)
GEMINI_MAX_OUTPUT_TOKENS=null      # → 200 (достатньо для JSON)
GEMINI_TOP_P=1.0                   # → 0.95 (меньше варіативності)
GEMINI_TOP_K=40                    # → 20 (більш детермінована)

# НОВІ ПАРАМЕТРИ:
GEMINI_FREQUENCY_PENALTY=0.0       # + 0.1 (уникати повторень)
GEMINI_PRESENCE_PENALTY=0.0        # + 0.05 (більше різноманітності)
```

**Рекомендовані значення для JSON tagging:**
```env
# Профіль: "Stable JSON Output"
GEMINI_TEMPERATURE=0.2
GEMINI_TOP_P=0.95
GEMINI_TOP_K=20
GEMINI_MAX_OUTPUT_TOKENS=200
```

---

## 🎯 Пріоритет 3: ЦІКАВО (за 2 тижні)

### 3.1 Запровадити Batching для tag-space операцій

**Поточна ситуація:** Кожна сторінка = окремий API запит

**Оптимізація:**
```python
# Замість:
for page in pages:
    tags = await gemini.tag_page(page.body)  # ← кожен запит окремо

# Краще:
async def batch_tag_pages(pages: List[Page], batch_size: int = 5):
    """Обробляйте сторінки батчами з контролем паралелізму"""
    
    semaphore = asyncio.Semaphore(batch_size)  # макс 5 паралельних
    
    async def tag_with_limit(page):
        async with semaphore:
            await rate_limiter.wait_if_needed()
            return await gemini.tag_page(page.body)
    
    tasks = [tag_with_limit(page) for page in pages]
    return await asyncio.gather(*tasks)
```

**Очікуваний результат:** + 3x швидше для bulk операцій (при контрольованій паралельності)

---

### 3.2 Реалізувати Monitoring Dashboard

**Файл для створення:** `src/core/ai/monitoring.py`

```python
from dataclasses import dataclass, field
from typing import Dict, List
from datetime import datetime, timedelta

@dataclass
class ProviderMetrics:
    provider: str
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    rate_limit_errors: int = 0
    total_tokens_used: int = 0
    total_cost_usd: float = 0.0
    avg_latency_ms: float = 0.0
    last_error: str = ""
    last_error_time: datetime = None
    
    @property
    def success_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return (self.successful_requests / self.total_requests) * 100
    
    @property
    def is_healthy(self) -> bool:
        return self.success_rate >= 95.0

# Монітор
class AIProviderMonitor:
    def __init__(self):
        self.metrics: Dict[str, ProviderMetrics] = {}
    
    def record_request(self, provider: str, success: bool, 
                      latency_ms: float, tokens: int, cost: float,
                      error: str = None):
        if provider not in self.metrics:
            self.metrics[provider] = ProviderMetrics(provider=provider)
        
        m = self.metrics[provider]
        m.total_requests += 1
        
        if success:
            m.successful_requests += 1
        else:
            m.failed_requests += 1
            if "429" in (error or ""):
                m.rate_limit_errors += 1
            m.last_error = error
            m.last_error_time = datetime.now()
        
        m.total_tokens_used += tokens
        m.total_cost_usd += cost
        m.avg_latency_ms = (m.avg_latency_ms * (m.total_requests - 1) + latency_ms) / m.total_requests
    
    def get_report(self) -> str:
        report = "📊 AI Provider Health Report\n"
        report += "=" * 60 + "\n"
        
        for provider_name, metrics in self.metrics.items():
            status = "✅" if metrics.is_healthy else "⚠️"
            report += f"\n{status} {provider_name.upper()}\n"
            report += f"  Success Rate: {metrics.success_rate:.1f}%\n"
            report += f"  Requests: {metrics.successful_requests}/{metrics.total_requests}\n"
            report += f"  Avg Latency: {metrics.avg_latency_ms:.0f}ms\n"
            report += f"  Tokens: {metrics.total_tokens_used:,}\n"
            report += f"  Cost: ${metrics.total_cost_usd:.3f}\n"
            
            if metrics.rate_limit_errors > 0:
                report += f"  ⚠️ Rate Limits: {metrics.rate_limit_errors}\n"
        
        return report

MONITOR = AIProviderMonitor()
```

**Використання:**
```python
# Логувати кожен запит
MONITOR.record_request(
    provider="gemini",
    success=True,
    latency_ms=1532,
    tokens=5163,
    cost=0.0015
)

# Вивести звіт
print(MONITOR.get_report())
```

---

## 📋 ЧЕКЛИСТ РЕАЛІЗАЦІЇ

### Негайно (1-2 дні)
- [ ] Перевірити Gemini API quotas у Google Cloud Console
- [ ] Upgrade на Paid tier (якщо потрібно)
- [ ] Реалізувати exponential backoff у `gemini_client.py`

### Цей тиждень
- [ ] Створити `rate_limiter.py`
- [ ] Інтегрувати rate limiter в GeminiClient
- [ ] Оптимізувати prompt (скоротити з 4465 на 2000-2500 tokens)
- [ ] Оновити `.env` з новими параметрами Gemini
- [ ] Тестування з новими параметрами

### Наступний тиждень
- [ ] Реалізувати batch tagging для tag-space операцій
- [ ] Додати monitoring dashboard
- [ ] Performance тестування з новою конфігурацією
- [ ] Документувати оптимізовані параметри

---

## 🎯 ОЧІКУВАНІ РЕЗУЛЬТАТИ

| Метрика | Поточна | Очікувана | Вдосконалення |
|---------|---------|-----------|---------------|
| **Gemini Success Rate** | 40% | 95%+ | +140% |
| **Avg Latency (Gemini)** | 1.5s | 1.0s | -33% |
| **Cost per operation** | $0.012 (fallback) | $0.0003 | -97% |
| **Stability** | Нестабільна | Стабільна | Критична ✅ |
| **Throughput (pages/min)** | ~30 | ~60+ | +100% |

---

**Версія документу:** 1.0  
**Дата:** 2026-01-03  
**Статус:** Ready for implementation
