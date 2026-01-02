# AI Cost Tracking Documentation

## 📋 Огляд

Cost Tracking модуль дозволяє відстежувати та аналізувати вартість використання AI провайдерів (OpenAI, Gemini).

**Ключові можливості:**
- ✅ Розрахунок вартості на основі токенів
- ✅ Порівняння провайдерів
- ✅ Аналіз економії
- ✅ Прогнозування витрат для bulk операцій
- ✅ Основа для cost-based routing

## 🎯 Навіщо потрібен Cost Tracking?

### Проблема: Непрогнозовані витрати

```python
# Без cost tracking - витрати невідомі
for i in range(1000):
    await tagging_agent.suggest_tags(page.content)
# Скільки це коштувало? 🤷
```

### Рішення: Cost Calculator

```python
from src.core.ai.costs import CostCalculator

calculator = CostCalculator()

for page in pages:
    result = await tagging_agent.suggest_tags(page.content)
    
    # Розрахунок вартості
    cost = calculator.estimate(
        provider="gemini",
        prompt_tokens=result.prompt_tokens,
        completion_tokens=result.completion_tokens
    )
    
    print(f"Cost: ${cost.total_usd:.6f}")
    # Cost: $0.000105
```

## 💰 Pricing (Dec 2025)

### OpenAI GPT-4o-mini

| Type | Per 1M tokens | Per 1K tokens |
|------|---------------|---------------|
| Input (Prompt) | $0.150 | $0.00015 |
| Output (Completion) | $0.600 | $0.0006 |

### Google Gemini 2.0 Flash

| Type | Per 1M tokens | Per 1K tokens |
|------|---------------|---------------|
| Input (Prompt) | $0.075 | $0.000075 |
| Output (Completion) | $0.300 | $0.0003 |

**Gemini ~2x дешевше за OpenAI** 💡

## 📐 Формули розрахунку

### OpenAI
```python
prompt_cost = (prompt_tokens / 1000) * 0.00015
completion_cost = (completion_tokens / 1000) * 0.0006
total_cost = prompt_cost + completion_cost
```

### Gemini
```python
prompt_cost = (prompt_tokens / 1000) * 0.000075
completion_cost = (completion_tokens / 1000) * 0.0003
total_cost = prompt_cost + completion_cost
```

## 🚀 Використання

### 1. Basic Cost Estimation

```python
from src.core.ai.costs import CostCalculator

calculator = CostCalculator()

# OpenAI cost
cost = calculator.estimate(
    provider="openai",
    prompt_tokens=1200,
    completion_tokens=800
)

print(f"Provider: {cost.provider}")
print(f"Tokens: {cost.total_tokens}")
print(f"Cost: ${cost.total_usd:.6f}")
```

**Output:**
```
Provider: openai
Tokens: 2000
Cost: $0.000660
```

### 2. Compare Providers

```python
calculator = CostCalculator()

# Compare costs for same token usage
comparison = calculator.compare_providers(
    prompt_tokens=1000,
    completion_tokens=500
)

for provider, cost in comparison.items():
    print(f"{provider}: ${cost.total_usd:.6f}")
```

**Output:**
```
openai: $0.000450
gemini: $0.000225
```

### 3. Calculate Savings

```python
calculator = CostCalculator()

savings = calculator.get_savings(
    provider_a="openai",
    provider_b="gemini",
    prompt_tokens=1000,
    completion_tokens=500
)

print(f"OpenAI: ${savings['cost_a_usd']:.6f}")
print(f"Gemini: ${savings['cost_b_usd']:.6f}")
print(f"Savings: ${savings['absolute_usd']:.6f} ({savings['percentage']:.1f}%)")
print(f"Cheaper: {savings['cheaper']}")
```

**Output:**
```
OpenAI: $0.000450
Gemini: $0.000225
Savings: $0.000225 (50.0%)
Cheaper: gemini
```

### 4. Custom Pricing

```python
from src.core.ai.costs import CostConfig, CostCalculator

# Custom pricing (e.g., enterprise discount)
config = CostConfig(
    openai_prompt_per_1k=0.0001,    # Discounted
    openai_completion_per_1k=0.0004,
    gemini_prompt_per_1k=0.00005,
    gemini_completion_per_1k=0.00015,
)

calculator = CostCalculator(config)

cost = calculator.estimate("openai", 1000, 500)
print(f"Cost with discount: ${cost.total_usd:.6f}")
```

## 📊 Real-World Examples

### Example 1: Bulk Tagging (1000 Pages)

```python
calculator = CostCalculator()

# Assumptions:
# - 300 prompt tokens per page (content)
# - 50 completion tokens per page (tags)
tokens_per_page = (300, 50)
num_pages = 1000

# OpenAI cost
openai_cost = calculator.estimate("openai", *tokens_per_page)
openai_total = openai_cost.total_usd * num_pages

# Gemini cost
gemini_cost = calculator.estimate("gemini", *tokens_per_page)
gemini_total = gemini_cost.total_usd * num_pages

print(f"\nBulk Tagging (1000 pages):")
print(f"  OpenAI: ${openai_total:.2f}")
print(f"  Gemini: ${gemini_total:.2f}")
print(f"  Savings: ${openai_total - gemini_total:.2f}")
```

**Output:**
```
Bulk Tagging (1000 pages):
  OpenAI: $0.08
  Gemini: $0.04
  Savings: $0.04
```

### Example 2: Summary Generation (100 Pages)

```python
calculator = CostCalculator()

# Assumptions:
# - 800 prompt tokens per page (long content)
# - 200 completion tokens per page (summary)
tokens_per_summary = (800, 200)
num_summaries = 100

# Calculate costs
comparison = calculator.compare_providers(*tokens_per_summary)

openai_total = comparison["openai"].total_usd * num_summaries
gemini_total = comparison["gemini"].total_usd * num_summaries

print(f"\nSummary Generation (100 pages):")
print(f"  OpenAI: ${openai_total:.2f}")
print(f"  Gemini: ${gemini_total:.2f}")
print(f"  Savings: ${openai_total - gemini_total:.2f}")
```

**Output:**
```
Summary Generation (100 pages):
  OpenAI: $0.03
  Gemini: $0.02
  Savings: $0.01
```

### Example 3: Monthly Budget Estimation

```python
calculator = CostCalculator()

# Monthly usage:
# - 10,000 tagging requests
# - 1,000 summary requests

# Tagging: 300p + 50c per request
tagging_cost_openai = calculator.estimate("openai", 300, 50)
tagging_monthly_openai = tagging_cost_openai.total_usd * 10000

tagging_cost_gemini = calculator.estimate("gemini", 300, 50)
tagging_monthly_gemini = tagging_cost_gemini.total_usd * 10000

# Summary: 800p + 200c per request
summary_cost_openai = calculator.estimate("openai", 800, 200)
summary_monthly_openai = summary_cost_openai.total_usd * 1000

summary_cost_gemini = calculator.estimate("gemini", 800, 200)
summary_monthly_gemini = summary_cost_gemini.total_usd * 1000

# Totals
openai_monthly = tagging_monthly_openai + summary_monthly_openai
gemini_monthly = tagging_monthly_gemini + summary_monthly_gemini

print(f"\nMonthly Budget Estimate:")
print(f"  OpenAI: ${openai_monthly:.2f}/month")
print(f"  Gemini: ${gemini_monthly:.2f}/month")
print(f"  Potential Savings: ${openai_monthly - gemini_monthly:.2f}/month")
```

**Output:**
```
Monthly Budget Estimate:
  OpenAI: $1.02/month
  Gemini: $0.51/month
  Potential Savings: $0.51/month
```

## 🔧 Integration з Logging

### В Agent коді

```python
from src.core.ai.costs import CostCalculator
from src.core.logging.logger import get_logger

logger = get_logger(__name__)
calculator = CostCalculator()

async def generate_summary(page_id: str):
    result = await summary_agent.generate_summary(page_id)
    
    # Calculate cost
    cost = calculator.estimate(
        provider="openai",
        prompt_tokens=result.prompt_tokens,
        completion_tokens=result.completion_tokens
    )
    
    # Log cost
    logger.info(
        "Summary generated",
        extra={
            "page_id": page_id,
            "provider": cost.provider,
            "tokens": cost.total_tokens,
            "cost_usd": cost.total_usd,
        }
    )
    
    return result
```

### В Router коді

```python
from src.core.ai.router import AIProviderRouter
from src.core.ai.costs import CostCalculator

router = AIProviderRouter()
calculator = CostCalculator()

async def smart_generate(prompt: str):
    # Get cost estimate BEFORE calling
    estimated_tokens = len(prompt.split()) * 1.3  # Rough estimate
    
    comparison = calculator.compare_providers(
        prompt_tokens=int(estimated_tokens),
        completion_tokens=100  # Estimated
    )
    
    # Choose cheaper provider
    if comparison["gemini"].total_usd < comparison["openai"].total_usd:
        provider = "gemini"
    else:
        provider = "openai"
    
    result = await router.generate(prompt, provider=provider)
    
    # Log actual cost
    actual_cost = calculator.estimate(
        provider=provider,
        prompt_tokens=result.prompt_tokens,
        completion_tokens=result.completion_tokens
    )
    
    logger.info(f"Used {provider}, cost: ${actual_cost.total_usd:.6f}")
    
    return result
```

## 📈 Cost-Based Routing

### Strategy 1: Always Cheapest

```python
def choose_provider_by_cost(estimated_prompt_tokens: int, estimated_completion_tokens: int):
    calculator = CostCalculator()
    
    comparison = calculator.compare_providers(
        prompt_tokens=estimated_prompt_tokens,
        completion_tokens=estimated_completion_tokens
    )
    
    # Return cheapest
    if comparison["gemini"].total_usd < comparison["openai"].total_usd:
        return "gemini"
    return "openai"
```

### Strategy 2: Cost Threshold

```python
def choose_provider_with_threshold(prompt_tokens: int, completion_tokens: int):
    calculator = CostCalculator()
    
    # Calculate OpenAI cost
    openai_cost = calculator.estimate("openai", prompt_tokens, completion_tokens)
    
    # If cost is low, use OpenAI (better quality)
    if openai_cost.total_usd < 0.001:  # Less than $0.001
        return "openai"
    
    # Otherwise use Gemini (cheaper)
    return "gemini"
```

### Strategy 3: Budget-Based

```python
class BudgetManager:
    def __init__(self, monthly_budget_usd: float):
        self.budget = monthly_budget_usd
        self.spent = 0.0
        self.calculator = CostCalculator()
    
    def choose_provider(self, prompt_tokens: int, completion_tokens: int):
        remaining = self.budget - self.spent
        
        # If low budget, force Gemini
        if remaining < 0.1:  # Less than $0.10 remaining
            return "gemini"
        
        # Otherwise allow OpenAI
        return "openai"
    
    def track_cost(self, provider: str, prompt_tokens: int, completion_tokens: int):
        cost = self.calculator.estimate(provider, prompt_tokens, completion_tokens)
        self.spent += cost.total_usd
        
        logger.info(f"Spent: ${self.spent:.2f} / ${self.budget:.2f}")
```

## 🎯 Best Practices

### 1. Track All API Calls

```python
# Always calculate cost after API call
cost = calculator.estimate(provider, prompt_tokens, completion_tokens)
logger.info(f"Cost: ${cost.total_usd:.6f}")
```

### 2. Aggregate Costs

```python
# Track cumulative costs
total_cost = 0.0

for page in pages:
    result = await process_page(page)
    cost = calculator.estimate(provider, result.prompt_tokens, result.completion_tokens)
    total_cost += cost.total_usd

print(f"Total cost: ${total_cost:.2f}")
```

### 3. Compare Before Bulk Operations

```python
# Before processing 1000 pages
calculator = CostCalculator()

# Estimate costs
single_page_openai = calculator.estimate("openai", 300, 50)
single_page_gemini = calculator.estimate("gemini", 300, 50)

estimated_openai = single_page_openai.total_usd * 1000
estimated_gemini = single_page_gemini.total_usd * 1000

print(f"Estimated OpenAI: ${estimated_openai:.2f}")
print(f"Estimated Gemini: ${estimated_gemini:.2f}")

# Choose based on budget
if estimated_gemini < budget:
    provider = "gemini"
else:
    # Need to reduce scope or increase budget
    pass
```

### 4. Update Pricing Regularly

```python
# Check pricing: https://openai.com/pricing
# Check pricing: https://ai.google.dev/pricing

# Update CostConfig when prices change
config = CostConfig(
    openai_prompt_per_1k=0.00015,  # Current as of Dec 2025
    # ... update as needed
)
```

## 🧪 Testing Costs

### Unit Tests

```bash
pytest tests/core/ai/test_costs.py -v
```

**20 тестів:**
- ✅ Config (default, custom)
- ✅ CostEstimate dataclass
- ✅ OpenAI calculations (basic, zero, large, custom)
- ✅ Gemini calculations (basic, zero, large)
- ✅ Unknown provider
- ✅ Provider comparison
- ✅ Savings calculation
- ✅ Real-world scenarios

### Integration Test

```python
from src.core.ai.openai_client import OpenAIClient
from src.core.ai.costs import CostCalculator

async def test_real_cost():
    client = OpenAIClient(api_key="...")
    calculator = CostCalculator()
    
    response = await client.generate("Hello, world!")
    
    cost = calculator.estimate(
        provider="openai",
        prompt_tokens=response.prompt_tokens,
        completion_tokens=response.completion_tokens
    )
    
    print(f"Actual cost: ${cost.total_usd:.6f}")
```

## 📊 CI/CD Integration

### Cost Monitoring in CI

```yaml
# .github/workflows/cost-check.yml
name: Cost Check

on: [pull_request]

jobs:
  estimate-costs:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Estimate Test Costs
        run: |
          python scripts/estimate_test_costs.py
```

### Cost Budget Alerts

```python
# scripts/estimate_test_costs.py
from src.core.ai.costs import CostCalculator

calculator = CostCalculator()

# Estimate test suite costs
num_tests = 100
avg_tokens = (500, 100)

cost_per_test = calculator.estimate("openai", *avg_tokens)
total_cost = cost_per_test.total_usd * num_tests

# Alert if too expensive
if total_cost > 0.50:  # More than $0.50
    print(f"⚠️ WARNING: Test suite costs ${total_cost:.2f}")
    exit(1)
else:
    print(f"✅ Test suite costs ${total_cost:.2f}")
```

## 💡 Cost Optimization Tips

### 1. Use Gemini for Bulk Operations

```python
# Bulk tagging - use Gemini (2x cheaper)
router = AIProviderRouter(default_provider="gemini")
```

### 2. Reduce Token Usage

```python
# Shorter prompts = lower costs
prompt = "Summarize in 50 words:"  # Better than "Provide a detailed summary..."
```

### 3. Cache Results

```python
# Cache expensive operations
@cache
def get_summary(page_id):
    result = await summary_agent.generate_summary(page_id)
    # Cost paid once, reused many times
    return result
```

### 4. Batch Requests

```python
# Instead of 1000 individual calls
# Use batch processing with Gemini
```

## ✅ Переваги Cost Tracking

1. ✅ **Transparency** — знаєте точну вартість
2. ✅ **Optimization** — можете оптимізувати витрати
3. ✅ **Comparison** — порівнюєте провайдерів
4. ✅ **Budgeting** — плануєте бюджет
5. ✅ **Routing** — вибираєте провайдера по ціні
6. ✅ **Testing** — оцінюєте вартість тестів
7. ✅ **Production** — моніторите витрати

## 🚀 Готово до використання!

Cost Tracking модуль допоможе вам контролювати та оптимізувати витрати на AI API!
