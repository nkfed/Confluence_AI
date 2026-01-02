# AI Routing Inspector Documentation

## 📋 Огляд

**Routing Inspector** — це діагностичний інструмент для AI Provider Router, який надає детальну інформацію про стан маршрутизації.

**Ключові можливості:**
- ✅ Перевірка routing mode та провайдерів
- ✅ Моніторинг health status
- ✅ Верифікація API keys
- ✅ Інспекція моделей
- ✅ Pre-deployment checks
- ✅ Debugging та troubleshooting

## 🎯 Навіщо потрібен Routing Inspector?

### Проблема: Невидимий стан маршрутизації

```python
# Який провайдер буде використаний?
router = AIProviderRouter()
response = await router.generate("prompt")  # OpenAI? Gemini? 🤷

# Чому fallback не працює?
# Які моделі використовуються?
# Чи правильно налаштовані ключі?
```

### Рішення: Inspect перед використанням

```python
from src.core.ai.router import AIProviderRouter

router = AIProviderRouter()

# Інспектуємо стан
report = await router.explain()

print(f"Mode: {report['routing_mode']}")
print(f"Primary: {report['default_provider']}")
print(f"Fallback: {report['fallback_provider']}")
print(f"All OK: {report['all_providers_ok']}")

# Тепер знаємо, що відбувається!
```

## 🔍 Метод `explain()`

### Signature

```python
async def explain(self, settings: Optional[AISettings] = None) -> dict:
    """
    Return detailed diagnostics of current AI routing state.
    
    Args:
        settings: AI settings (uses default if not provided)
        
    Returns:
        dict: Comprehensive routing diagnostics
    """
```

### Що повертає

```python
{
    "routing_mode": str,              # A, B, C, or D
    "default_provider": str,          # "openai" or "gemini"
    "fallback_provider": str | None,  # Fallback provider name
    "registered_providers": list,     # ["gemini", "openai"]
    "models": {
        "openai": str,                # Model name
        "gemini": str,                # Model name
    },
    "api_keys": {
        "openai": bool,               # True if key is set
        "gemini": bool,               # True if key is set
    },
    "health": {
        "openai": {
            "ok": bool,               # Health status
            "error": str | None,      # Error message if unhealthy
            "details": dict | None,   # Additional details
        },
        "gemini": {
            "ok": bool,
            "error": str | None,
            "details": dict | None,
        },
    },
    "all_providers_ok": bool,         # True if all healthy
}
```

## 🚀 Використання

### 1. Basic Inspection

```python
from src.core.ai.router import AIProviderRouter

router = AIProviderRouter()

# Get routing diagnostics
report = await router.explain()

# Display report
import json
print(json.dumps(report, indent=2))
```

**Output:**
```json
{
  "routing_mode": "A",
  "default_provider": "openai",
  "fallback_provider": "gemini",
  "registered_providers": ["gemini", "openai"],
  "models": {
    "openai": "gpt-4o-mini",
    "gemini": "gemini-2.0-flash-exp"
  },
  "api_keys": {
    "openai": true,
    "gemini": true
  },
  "health": {
    "openai": {
      "ok": true,
      "error": null,
      "details": {
        "model": "gpt-4o-mini",
        "total_tokens": 9,
        "provider": "openai"
      }
    },
    "gemini": {
      "ok": true,
      "error": null,
      "details": {
        "model": "gemini-2.0-flash-exp",
        "tokens_for_ping": 1
      }
    }
  },
  "all_providers_ok": true
}
```

### 2. Pre-deployment Check

```python
from src.core.ai.router import AIProviderRouter
from src.core.config.ai_settings import AISettings

# Initialize router
router = AIProviderRouter()
settings = AISettings()

# Inspect before deployment
report = await router.explain(settings)

# Validate configuration
assert report['all_providers_ok'], "❌ Providers not healthy!"
assert report['api_keys']['openai'], "❌ OpenAI key missing!"
assert report['api_keys']['gemini'], "❌ Gemini key missing!"

print("✅ Pre-deployment checks passed!")
```

### 3. Debug Routing Issues

```python
async def debug_routing_issue():
    router = AIProviderRouter()
    report = await router.explain()
    
    # Check routing mode
    if report['routing_mode'] != 'A':
        print(f"⚠️ Unexpected mode: {report['routing_mode']}")
    
    # Check providers
    if not report['all_providers_ok']:
        unhealthy = [
            name for name, health in report['health'].items()
            if not health['ok']
        ]
        print(f"❌ Unhealthy providers: {unhealthy}")
        
        for name in unhealthy:
            error = report['health'][name]['error']
            print(f"  {name}: {error}")
    
    # Check API keys
    for provider, has_key in report['api_keys'].items():
        if not has_key:
            print(f"⚠️ Missing API key for {provider}")
    
    # Check models
    print(f"Models: {report['models']}")
```

### 4. Environment Verification

```python
import os
from src.core.ai.router import AIProviderRouter
from src.core.config.ai_settings import AISettings

async def verify_environment():
    """Verify AI environment is properly configured"""
    
    # Load settings
    settings = AISettings()
    
    # Create router
    router = AIProviderRouter()
    
    # Get report
    report = await router.explain(settings)
    
    print("=" * 60)
    print("AI ENVIRONMENT VERIFICATION")
    print("=" * 60)
    
    # Routing Mode
    print(f"\n[Routing]")
    print(f"  Mode: {report['routing_mode']}")
    print(f"  Primary: {report['default_provider']}")
    print(f"  Fallback: {report['fallback_provider'] or 'None'}")
    
    # Providers
    print(f"\n[Providers]")
    print(f"  Registered: {', '.join(report['registered_providers'])}")
    
    # Models
    print(f"\n[Models]")
    for provider, model in report['models'].items():
        print(f"  {provider}: {model}")
    
    # API Keys
    print(f"\n[API Keys]")
    for provider, has_key in report['api_keys'].items():
        status = "✅" if has_key else "❌"
        print(f"  {provider}: {status}")
    
    # Health
    print(f"\n[Health]")
    for provider, health in report['health'].items():
        status = "✅" if health['ok'] else "❌"
        print(f"  {provider}: {status}")
        if not health['ok']:
            print(f"    Error: {health['error']}")
    
    # Overall Status
    print(f"\n[Overall]")
    if report['all_providers_ok']:
        print("  Status: ✅ ALL OK")
    else:
        print("  Status: ❌ ISSUES DETECTED")
    
    print("=" * 60)
    
    return report['all_providers_ok']

# Run verification
if await verify_environment():
    print("\n✅ Environment is ready!")
else:
    print("\n❌ Please fix issues before proceeding")
```

## 📊 Use Cases

### Use Case 1: Configuration Changes

```python
# After changing .env file
print("Checking new configuration...")

router = AIProviderRouter()
report = await router.explain()

# Verify changes
if report['routing_mode'] == 'B':
    print("✅ Routing mode changed to B (Gemini primary)")
else:
    print(f"⚠️ Mode is {report['routing_mode']}, expected B")

if report['default_provider'] == 'gemini':
    print("✅ Primary provider is now Gemini")
```

### Use Case 2: A/B Testing

```python
async def prepare_ab_test():
    """Prepare for A/B testing"""
    
    router = AIProviderRouter()
    report = await router.explain()
    
    # Verify both providers are healthy
    if not report['all_providers_ok']:
        raise RuntimeError("Cannot run A/B test: providers unhealthy")
    
    # Verify both keys are set
    if not all(report['api_keys'].values()):
        raise RuntimeError("Cannot run A/B test: missing API keys")
    
    print("✅ Ready for A/B testing")
    print(f"  Provider A: {report['default_provider']}")
    print(f"  Provider B: {report['fallback_provider']}")
    
    return report
```

### Use Case 3: CI/CD Validation

```python
#!/usr/bin/env python
"""
CI/CD validation script for AI routing configuration.
"""

import asyncio
import sys
from src.core.ai.router import AIProviderRouter

async def validate_ci_cd():
    """Validate AI routing in CI/CD pipeline"""
    
    router = AIProviderRouter()
    report = await router.explain()
    
    errors = []
    
    # Check API keys
    for provider, has_key in report['api_keys'].items():
        if not has_key:
            errors.append(f"Missing API key for {provider}")
    
    # Check health
    for provider, health in report['health'].items():
        if not health['ok']:
            errors.append(f"{provider} unhealthy: {health['error']}")
    
    # Report results
    if errors:
        print("❌ CI/CD Validation FAILED")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)
    else:
        print("✅ CI/CD Validation PASSED")
        print(f"  Mode: {report['routing_mode']}")
        print(f"  Primary: {report['default_provider']}")
        print(f"  Providers: {len(report['registered_providers'])}")
        sys.exit(0)

if __name__ == "__main__":
    asyncio.run(validate_ci_cd())
```

### Use Case 4: Health Dashboard

```python
from fastapi import FastAPI
from src.core.ai.router import AIProviderRouter

app = FastAPI()
router = AIProviderRouter()

@app.get("/health/ai/routing")
async def ai_routing_health():
    """
    AI Routing Health endpoint for monitoring dashboards.
    
    Returns:
        Detailed routing diagnostics
    """
    report = await router.explain()
    
    return {
        "status": "healthy" if report['all_providers_ok'] else "degraded",
        "routing": {
            "mode": report['routing_mode'],
            "primary": report['default_provider'],
            "fallback": report['fallback_provider'],
        },
        "providers": report['health'],
        "configuration": {
            "models": report['models'],
            "keys_configured": report['api_keys'],
        },
    }
```

## 🎯 Best Practices

### 1. Check Before Starting

```python
# Always inspect before starting agents
router = AIProviderRouter()
report = await router.explain()

if not report['all_providers_ok']:
    print("⚠️ Warning: Some providers unhealthy")
    # Decide whether to proceed or abort

# Start agents
agent = SummaryAgent(ai_router=router)
```

### 2. Log Routing State

```python
import logging
from src.core.ai.router import AIProviderRouter

logger = logging.getLogger(__name__)

async def log_routing_state():
    router = AIProviderRouter()
    report = await router.explain()
    
    logger.info(
        "AI Routing State",
        extra={
            "mode": report['routing_mode'],
            "primary": report['default_provider'],
            "all_ok": report['all_providers_ok'],
        }
    )
```

### 3. Periodic Health Checks

```python
import asyncio
from src.core.ai.router import AIProviderRouter

async def periodic_health_check(interval_seconds=300):
    """Check AI routing health every 5 minutes"""
    
    router = AIProviderRouter()
    
    while True:
        report = await router.explain()
        
        if not report['all_providers_ok']:
            print(f"⚠️ [Health Check] Issues detected!")
            for name, health in report['health'].items():
                if not health['ok']:
                    print(f"  {name}: {health['error']}")
        else:
            print(f"✅ [Health Check] All providers OK")
        
        await asyncio.sleep(interval_seconds)
```

### 4. Environment-Specific Checks

```python
import os
from src.core.ai.router import AIProviderRouter

async def environment_specific_checks():
    env = os.getenv("ENVIRONMENT", "development")
    
    router = AIProviderRouter()
    report = await router.explain()
    
    if env == "production":
        # Production requirements
        assert report['all_providers_ok'], "Production requires healthy providers"
        assert report['api_keys']['openai'], "Production requires OpenAI key"
        assert report['api_keys']['gemini'], "Production requires Gemini key"
    
    elif env == "development":
        # Development can work with one provider
        if not report['all_providers_ok']:
            print("⚠️ Development: Some providers unhealthy (acceptable)")
```

## 🧪 Testing

### Unit Tests

```bash
pytest tests/core/ai/test_router_inspector.py -v
```

**19 тестів:**
- ✅ Basic structure (6 tests)
- ✅ Models reporting (2 tests)
- ✅ API keys reporting (2 tests)
- ✅ Health reporting (3 tests)
- ✅ All providers OK (2 tests)
- ✅ Mocked health check (3 tests)
- ✅ Integration test (1 test)

### Integration Test

```python
import pytest
from src.core.ai.router import AIProviderRouter
from src.core.config.ai_settings import AISettings

@pytest.mark.asyncio
async def test_real_routing_inspection():
    """Test real routing inspection with actual API keys"""
    
    settings = AISettings()
    router = AIProviderRouter()
    
    # Get real report
    report = await router.explain(settings)
    
    # Verify structure
    assert "routing_mode" in report
    assert "default_provider" in report
    assert "health" in report
    
    # Log results
    print(f"\nRouting Mode: {report['routing_mode']}")
    print(f"Primary: {report['default_provider']}")
    print(f"All OK: {report['all_providers_ok']}")
```

## 💡 Tips & Tricks

### 1. Pretty Print Report

```python
import json
from src.core.ai.router import AIProviderRouter

async def pretty_print_routing():
    router = AIProviderRouter()
    report = await router.explain()
    
    print(json.dumps(report, indent=2, sort_keys=True))
```

### 2. Extract Specific Info

```python
async def get_primary_provider():
    router = AIProviderRouter()
    report = await router.explain()
    return report['default_provider']

async def is_fallback_available():
    router = AIProviderRouter()
    report = await router.explain()
    return report['fallback_provider'] is not None

async def are_all_providers_healthy():
    router = AIProviderRouter()
    report = await router.explain()
    return report['all_providers_ok']
```

### 3. Compare Configurations

```python
from src.core.config.ai_settings import AISettings

async def compare_routing_configs():
    """Compare two routing configurations"""
    
    router = AIProviderRouter()
    
    # Configuration A
    settings_a = AISettings(AI_ROUTING_MODE="A")
    report_a = await router.explain(settings_a)
    
    # Configuration B
    settings_b = AISettings(AI_ROUTING_MODE="B")
    report_b = await router.explain(settings_b)
    
    print("Configuration A:")
    print(f"  Primary: {report_a['default_provider']}")
    
    print("\nConfiguration B:")
    print(f"  Primary: {report_b['default_provider']}")
```

## ✅ Переваги Routing Inspector

1. ✅ **Visibility** — бачите повний стан маршрутизації
2. ✅ **Debugging** — швидко знаходите проблеми
3. ✅ **Validation** — перевіряєте конфігурацію
4. ✅ **Monitoring** — моніторите health status
5. ✅ **CI/CD** — автоматична валідація в pipeline
6. ✅ **Documentation** — самодокументуючийся код
7. ✅ **Troubleshooting** — діагностика помилок

## 🚀 Готово до використання!

Routing Inspector допоможе вам контролювати та діагностувати AI маршрутизацію в будь-який момент!
