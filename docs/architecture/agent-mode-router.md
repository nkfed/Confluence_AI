# Agent Mode Router

Централізована маршрутизація запитів за режимами роботи агентів.

## Компоненти

### 1. AgentModeResolver
**Файл:** `src/core/agent_mode_resolver.py`

Централізований резолвер для визначення режимів та whitelist з розширеними методами перевірки дозволів.

**Основні методи:**

```python
class AgentModeResolver:
    def get_mode() -> str
        """Повертає поточний режим (TEST, SAFE_TEST, PROD)"""
    
    def is_allowed(space_key: str, page_id: str) -> bool
        """Перевіряє дозвіл для операції"""
    
    def should_dry_run() -> bool
        """Визначає чи потрібен dry_run"""
```

**Приклади використання:**

```python
from src.core.agent_mode_resolver import AgentModeResolver

resolver = AgentModeResolver()

# Проверка режима
mode = resolver.get_mode()  # 'TEST' | 'SAFE_TEST' | 'PROD'

# Проверка дозволов
if not resolver.is_allowed('MYSPACE', '12345'):
    raise PermissionError("Space not in whitelist")

# Проверка dry_run
if resolver.should_dry_run():
    print("Running in dry-run mode")
```

---

### 2. Інтеграція з маршрутизацією

#### SummaryAgent
```python
from src.agents.summary_agent import SummaryAgent

agent = SummaryAgent()
result = await agent.generate_summary(
    page_id=page_id,
    confluence_client=client,
    # dry_run автоматично встановлюється через AgentModeResolver
)
```

#### TaggingAgent
```python
from src.agents.tagging_agent import TaggingAgent

agent = TaggingAgent()
tags = await agent.tag_page(
    page_id=page_id,
    space_key=space_key,
    # whitelist перевіряється через AgentModeResolver
)
```

#### BulkTaggingService
```python
from src.services.bulk_tagging_service import BulkTaggingService

service = BulkTaggingService(confluence_client)
result = await service.tag_pages(
    page_ids=[...],
    space_key=space_key,
    dry_run=dry_run  # Може бути перевизначено режимом
)
```

---

## Матриця маршрутизації

| Режим | Dry Run | Whitelist | Запис | Статус |
|-------|---------|-----------|-------|--------|
| TEST | ✅ (force) | ✅ (обов.) | ❌ | dry_run |
| SAFE_TEST | 🔀 (параметр) | ✅ (обов.) | ✅ (whitelist) | updated/dry_run |
| PROD | 🔀 (параметр) | ❌ (ignore) | ✅ | updated/dry_run |

---

## Дивіться також

- [Agent Modes Overview](./agent-modes-overview.md) — огляд режимів
- [Agent Mode Lifecycle](./agent-mode-lifecycle.md) — цикл життя
- [Agent Mode Error Handling](./agent-mode-errors.md) — обробка помилок

---

**Версія:** 2.0  
**Дата:** 2025-12-27
