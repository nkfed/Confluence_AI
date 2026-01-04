# 🎯 ACTION PLAN: Наступна ітерація оптимізації

## 📋 ЗМІНИ В .ENV

### Поточна конфігурація:
```env
TAG_SPACE_AI_CONCURRENCY=3
TAG_SPACE_MAX_AI_CONCURRENCY=10
TAG_SPACE_BATCH_SIZE=5
TAG_SPACE_CACHE_ENABLED=true
TAG_SPACE_CACHE_SIZE=1000
```

### Рекомендована конфігурація:
```env
# Базова одночасність (зменшена для більшої стабільності)
TAG_SPACE_AI_CONCURRENCY=2  # було 3 → тепер 2 для менших burst

# Максимальна одночасність (без змін)
TAG_SPACE_MAX_AI_CONCURRENCY=10

# Розмір батчу (без змін, працює добре)
TAG_SPACE_BATCH_SIZE=5

# Кешування (без змін, працює добре)
TAG_SPACE_CACHE_ENABLED=true
TAG_SPACE_CACHE_SIZE=1000

# === НОВІ ПАРАМЕТРИ ===

# Захист від rate limiting
TAG_SPACE_SAFE_BURST_SIZE=12  # Після стількох операцій — пауза
TAG_SPACE_COOLDOWN_SECONDS=30  # Тривалість паузи для відновлення квоти

# Exponential backoff для Gemini
GEMINI_RETRY_DELAYS=2,5,10  # Секунди між retry спробами
GEMINI_MAX_RETRIES=3  # Було 2 → тепер 3

# Adaptive concurrency (експериментально)
TAG_SPACE_ADAPTIVE_CONCURRENCY=false  # Увімкнути пізніше після тестування
TAG_SPACE_MIN_CONCURRENCY=1
TAG_SPACE_MAX_ADAPTIVE_CONCURRENCY=5
```

---

## 🔧 ЗМІНИ В КОДІ

### 1. Додати паузу після burst операцій

**Файл:** `src/api/routes/bulk_operations.py` (або відповідний)

```python
from src.config.settings import settings

async def tag_space_pages(pages: List[Page]):
    """Tag pages with rate limit protection"""
    
    # Параметри з .env
    safe_burst_size = int(os.getenv("TAG_SPACE_SAFE_BURST_SIZE", "12"))
    cooldown_seconds = int(os.getenv("TAG_SPACE_COOLDOWN_SECONDS", "30"))
    
    operation_count = 0
    results = []
    
    for page in pages:
        # Перевірка burst limit
        if operation_count >= safe_burst_size:
            logger.info(
                f"[RATE LIMIT PROTECTION] Processed {operation_count} operations. "
                f"Cooling down for {cooldown_seconds}s to avoid Gemini rate limits..."
            )
            await asyncio.sleep(cooldown_seconds)
            operation_count = 0  # Reset counter
        
        # Обробити сторінку
        result = await tag_single_page(page)
        results.append(result)
        operation_count += 1
    
    return results
```

---

### 2. Експоненціальний backoff для Gemini

**Файл:** `src/core/ai/gemini_client.py`

```python
class GeminiClient:
    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model
        
        # Retry configuration з .env
        retry_delays_str = os.getenv("GEMINI_RETRY_DELAYS", "2,5,10")
        self.retry_delays = [int(d) for d in retry_delays_str.split(",")]
        self.max_retries = int(os.getenv("GEMINI_MAX_RETRIES", "3"))
    
    async def generate(self, prompt: str, **kwargs) -> AIResponse:
        """Generate with exponential backoff"""
        
        for attempt in range(self.max_retries):
            try:
                response = await self._call_api(prompt, **kwargs)
                return response
            
            except HTTPStatusError as e:
                if e.status_code == 429:
                    if attempt < self.max_retries - 1:
                        # Exponential backoff
                        wait_time = self.retry_delays[attempt]
                        logger.warning(
                            f"[Gemini] Rate limit hit on attempt {attempt + 1}/{self.max_retries}. "
                            f"Waiting {wait_time}s before retry..."
                        )
                        await asyncio.sleep(wait_time)
                    else:
                        # Max retries exhausted
                        logger.error(f"[Gemini] Max retries ({self.max_retries}) reached. Giving up.")
                        raise RuntimeError(
                            f"Gemini rate limit error after {self.max_retries} attempts: {e}"
                        )
                else:
                    # Non-429 error — не retry
                    raise
```

---

### 3. Adaptive Concurrency (опціонально, для експериментів)

**Новий файл:** `src/core/ai/adaptive_concurrency.py`

```python
import asyncio
from dataclasses import dataclass
from src.core.logging import get_logger

logger = get_logger(__name__)

@dataclass
class AdaptiveConcurrencyManager:
    """Динамічно налаштовує concurrency на основі success/failure pattern"""
    
    min_concurrency: int = 1
    max_concurrency: int = 5
    current_concurrency: int = 1
    
    success_streak: int = 0
    failure_streak: int = 0
    
    # Thresholds
    increase_threshold: int = 5  # Після стількох успіхів — збільшити
    decrease_threshold: int = 2  # Після стількох помилок — зменшити
    
    def on_success(self):
        """Called after successful AI operation"""
        self.success_streak += 1
        self.failure_streak = 0
        
        # Збільшити concurrency після серії успіхів
        if (self.success_streak >= self.increase_threshold and 
            self.current_concurrency < self.max_concurrency):
            self.current_concurrency += 1
            logger.info(
                f"[ADAPTIVE] ✅ Success streak: {self.success_streak}. "
                f"Increasing concurrency to {self.current_concurrency}"
            )
            self.success_streak = 0  # Reset
    
    def on_failure_429(self):
        """Called after 429 rate limit error"""
        self.failure_streak += 1
        self.success_streak = 0
        
        # Зменшити concurrency після серії помилок
        if (self.failure_streak >= self.decrease_threshold and 
            self.current_concurrency > self.min_concurrency):
            self.current_concurrency -= 1
            logger.warning(
                f"[ADAPTIVE] ⚠️ Rate limit streak: {self.failure_streak}. "
                f"Decreasing concurrency to {self.current_concurrency}"
            )
            self.failure_streak = 0  # Reset
    
    def get_semaphore(self) -> asyncio.Semaphore:
        """Return semaphore with current concurrency limit"""
        return asyncio.Semaphore(self.current_concurrency)


# Глобальний менеджер
ADAPTIVE_MANAGER = AdaptiveConcurrencyManager(
    min_concurrency=int(os.getenv("TAG_SPACE_MIN_CONCURRENCY", "1")),
    max_concurrency=int(os.getenv("TAG_SPACE_MAX_ADAPTIVE_CONCURRENCY", "5")),
    current_concurrency=int(os.getenv("TAG_SPACE_AI_CONCURRENCY", "2"))
)
```

**Інтеграція:**

```python
# У bulk operations
async def tag_pages_with_adaptive_concurrency(pages: List[Page]):
    results = []
    
    for page in pages:
        semaphore = ADAPTIVE_MANAGER.get_semaphore()
        
        async with semaphore:
            try:
                result = await tag_page(page)
                ADAPTIVE_MANAGER.on_success()
                results.append(result)
            except RateLimitError:
                ADAPTIVE_MANAGER.on_failure_429()
                # Fallback to OpenAI
                result = await tag_page_openai(page)
                results.append(result)
    
    return results
```

---

## 📊 МОНІТОРИНГ

### Додати метрики для відстеження ефективності

**Новий файл:** `src/core/monitoring/tag_space_metrics.py`

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import List

@dataclass
class TagSpaceMetrics:
    """Metrics for tag-space operations"""
    
    total_operations: int = 0
    gemini_success: int = 0
    gemini_failures: int = 0
    openai_fallbacks: int = 0
    
    gemini_times: List[float] = field(default_factory=list)
    openai_times: List[float] = field(default_factory=list)
    
    start_time: datetime = field(default_factory=datetime.now)
    
    @property
    def gemini_success_rate(self) -> float:
        if self.total_operations == 0:
            return 0.0
        return (self.gemini_success / self.total_operations) * 100
    
    @property
    def avg_gemini_time(self) -> float:
        if not self.gemini_times:
            return 0.0
        return sum(self.gemini_times) / len(self.gemini_times)
    
    @property
    def avg_openai_time(self) -> float:
        if not self.openai_times:
            return 0.0
        return sum(self.openai_times) / len(self.openai_times)
    
    def record_gemini_success(self, duration_ms: float):
        self.total_operations += 1
        self.gemini_success += 1
        self.gemini_times.append(duration_ms)
    
    def record_gemini_failure(self):
        self.total_operations += 1
        self.gemini_failures += 1
    
    def record_openai_fallback(self, duration_ms: float):
        self.openai_fallbacks += 1
        self.openai_times.append(duration_ms)
    
    def generate_report(self) -> str:
        duration = (datetime.now() - self.start_time).total_seconds()
        
        report = f"""
╔════════════════════════════════════════════════════════════╗
║           TAG-SPACE OPERATION METRICS                      ║
╠════════════════════════════════════════════════════════════╣
║ Total Duration:        {duration:.1f} seconds              ║
║ Total Operations:      {self.total_operations}             ║
║                                                            ║
║ Gemini Success:        {self.gemini_success} ({self.gemini_success_rate:.1f}%)  ║
║ Gemini Failures:       {self.gemini_failures} ({100-self.gemini_success_rate:.1f}%) ║
║ OpenAI Fallbacks:      {self.openai_fallbacks}            ║
║                                                            ║
║ Avg Gemini Time:       {self.avg_gemini_time:.0f}ms       ║
║ Avg OpenAI Time:       {self.avg_openai_time:.0f}ms       ║
║                                                            ║
║ Throughput:            {self.total_operations/duration:.2f} ops/sec ║
╚════════════════════════════════════════════════════════════╝
        """
        return report


# Глобальний екземпляр
TAG_SPACE_METRICS = TagSpaceMetrics()
```

**Використання:**

```python
# В AI router або gemini_client
from src.core.monitoring.tag_space_metrics import TAG_SPACE_METRICS

# При успіху
TAG_SPACE_METRICS.record_gemini_success(duration_ms=860)

# При помилці
TAG_SPACE_METRICS.record_gemini_failure()

# При fallback
TAG_SPACE_METRICS.record_openai_fallback(duration_ms=1950)

# Вивести звіт в кінці
print(TAG_SPACE_METRICS.generate_report())
```

---

## ✅ ЧЕКЛИСТ РЕАЛІЗАЦІЇ

### Фаза 1: Критичні зміни (сьогодні)
- [ ] Оновити `.env` з новими параметрами
- [ ] Додати паузу після 12 операцій (safe burst protection)
- [ ] Реалізувати експоненціальний backoff в `gemini_client.py`
- [ ] Тестування на невеликому спейсі (5-10 сторінок)

### Фаза 2: Важливі покращення (завтра)
- [ ] Додати моніторинг метрик (`tag_space_metrics.py`)
- [ ] Інтегрувати метрики в існуючий код
- [ ] Запустити повний тест на спейсі "euheals"
- [ ] Порівняти результати з попередніми

### Фаза 3: Експериментальні можливості (цей тиждень)
- [ ] Реалізувати adaptive concurrency
- [ ] A/B тестування різних значень SAFE_BURST_SIZE
- [ ] Тонка настройка COOLDOWN_SECONDS
- [ ] Документувати оптимальні параметри

---

## 🎯 ОЧІКУВАНІ РЕЗУЛЬТАТИ

Після реалізації всіх змін очікуємо:

| Метрика | Поточне | Після змін | Покращення |
|---------|---------|------------|------------|
| **Gemini Success Rate** | 69% | **92%+** | +33% ✅ |
| **Fallback на OpenAI** | 31% | **<8%** | -74% ✅ |
| **Середній час/операцію** | 2.7 сек | **1.5 сек** | -44% ✅ |
| **Вартість за 100 операцій** | $0.40 | **$0.12** | -70% ✅ |

---

**Підготовлено:** AI Systems Implementation Team  
**Дата:** 2026-01-03  
**Пріоритет:** ВИСОКИЙ  
**Статус:** Ready for implementation
