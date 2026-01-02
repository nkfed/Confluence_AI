# Agent Mode Error Handling

Обробка помилок та debug механізми у системі агент-режимів.

## Типи помилок

### 1. Помилки авторизації

**Сценарій:** Користувач намагається отримати доступ до непозволеної сторінки

```python
# Приклад:
try:
    if not resolver.is_allowed(space_key, page_id):
        raise PermissionError(
            f"Page {page_id} in space {space_key} not in whitelist"
        )
except PermissionError as e:
    logger.warning(f"Access denied: {e}")
    return {
        "status": "error",
        "code": "PERMISSION_DENIED",
        "message": str(e)
    }
```

**Код помилки:** `PERMISSION_DENIED`  
**HTTP Status:** 403  
**Дія:** Логування, повернення помилки, без змін

---

### 2. Помилки конфігурації

**Сценарій:** AGENT_MODE невизначений або невалідний

```python
try:
    mode = resolver.get_mode()
    if mode not in ['TEST', 'SAFE_TEST', 'PROD']:
        raise ValueError(f"Invalid AGENT_MODE: {mode}")
except ValueError as e:
    logger.error(f"Configuration error: {e}")
    return {
        "status": "error",
        "code": "CONFIG_ERROR",
        "message": str(e)
    }
```

**Код помилки:** `CONFIG_ERROR`  
**HTTP Status:** 500  
**Дія:** Логування, зупинення операції

---

### 3. Помилки Confluence API

**Сценарій:** Confluence API недоступна або повертає помилку

```python
try:
    confluence_client = ConfluenceClient()
    page = await confluence_client.get_page(page_id)
except Exception as e:
    logger.error(f"Confluence API error: {e}")
    return {
        "status": "error",
        "code": "CONFLUENCE_ERROR",
        "message": str(e),
        "mode": mode
    }
```

**Код помилки:** `CONFLUENCE_ERROR`  
**HTTP Status:** 503  
**Дія:** Логування, зупинення операції, без змін у Confluence

---

### 4. Помилки обробки даних

**Сценарій:** Дані з Confluence непотрібного формату

```python
try:
    result = await agent.process(page_content)
except ValueError as e:
    logger.error(f"Data processing error: {e}")
    return {
        "status": "error",
        "code": "DATA_ERROR",
        "message": str(e),
        "page_id": page_id
    }
```

**Код помилки:** `DATA_ERROR`  
**HTTP Status:** 400  
**Дія:** Логування, зупинення операції

---

## Матриця помилок за режимом

| Помилка | TEST | SAFE_TEST | PROD |
|---------|------|-----------|------|
| PERMISSION_DENIED | Skip page | Block, 403 | Allow |
| CONFIG_ERROR | Fail | Fail | Fail |
| CONFLUENCE_ERROR | Fail | Fail | Fail |
| DATA_ERROR | Skip | Skip | Retry or Fail |

---

## Debug режим

### Активація

```dotenv
# .env
AGENT_MODE=TEST
DEBUG=true
LOG_LEVEL=DEBUG
```

### Вихідна інформація

При `DEBUG=true` логування містить:

```python
logger.debug(f"Mode: {mode}")
logger.debug(f"Whitelist allowed: {allowed_ids}")
logger.debug(f"Dry-run: {dry_run}")
logger.debug(f"Request: {request.dict()}")
logger.debug(f"Response: {response}")
```

### Приклад Debug вихідних даних

```
[2025-12-27 10:15:32] DEBUG - AgentModeResolver.get_mode() → 'SAFE_TEST'
[2025-12-27 10:15:32] DEBUG - WhitelistManager.get_allowed_ids('MYSPACE') → ['123', '456', '789']
[2025-12-27 10:15:33] DEBUG - Checking page 123 against whitelist: True
[2025-12-27 10:15:33] DEBUG - Setting dry_run=True (SAFE_TEST + dry_run=true in request)
[2025-12-27 10:15:34] DEBUG - TaggingAgent executing with dry_run=True
[2025-12-27 10:15:35] DEBUG - Result: {"status": "dry_run", "tags_added": [...]}
```

---

## Логування помилок

### Логічні файли

```
logs/
├── app.log           # Все логи
├── error.log         # Тільки помилки
├── debug.log         # Тільки DEBUG рівень
└── audit.log         # Audit trail (режими, операції)
```

### Формат логування

```python
import logging

logger = logging.getLogger(__name__)

# Info-рівень
logger.info(f"[{mode}] Operation started: tag_space(space={space_key}, pages={len(page_ids)})")

# Warning-рівень
logger.warning(f"[{mode}] Page {page_id} not in whitelist, skipping")

# Error-рівень
logger.error(f"[{mode}] Failed to process page {page_id}: {error}")

# Debug-рівень
logger.debug(f"[{mode}] Whitelist check: {is_allowed}")
```

---

## Обробка помилок у різних компонентах

### SummaryAgent

```python
from src.agents.summary_agent import SummaryAgent

try:
    agent = SummaryAgent()
    result = await agent.generate_summary(page_id)
except Exception as e:
    logger.error(f"SummaryAgent error: {e}")
    return {
        "status": "error",
        "code": "SUMMARY_ERROR",
        "page_id": page_id
    }
```

### TaggingAgent

```python
from src.agents.tagging_agent import TaggingAgent

try:
    agent = TaggingAgent()
    tags = await agent.tag_page(page_id, space_key)
except Exception as e:
    logger.error(f"TaggingAgent error: {e}")
    return {
        "status": "error",
        "code": "TAGGING_ERROR",
        "page_id": page_id
    }
```

### BulkTaggingService

```python
from src.services.bulk_tagging_service import BulkTaggingService

try:
    service = BulkTaggingService(confluence_client)
    result = await service.tag_pages(page_ids, space_key, dry_run)
except Exception as e:
    logger.error(f"BulkTaggingService error: {e}")
    return {
        "status": "error",
        "code": "BULK_SERVICE_ERROR",
        "affected_pages": len(page_ids),
        "message": str(e)
    }
```

---

## Тестування помилок

### Unit тести

```python
import pytest
from src.core.agent_mode_resolver import AgentModeResolver

def test_invalid_mode_raises_error():
    """Невалідний AGENT_MODE має викликати помилку"""
    with pytest.raises(ValueError):
        resolver = AgentModeResolver()
        resolver.validate_mode("INVALID")

def test_permission_denied():
    """Непозволена сторінка має повернути PERMISSION_DENIED"""
    resolver = AgentModeResolver(mode="SAFE_TEST")
    is_allowed = resolver.is_allowed("FORBIDDEN_SPACE", "12345")
    assert not is_allowed

def test_whitelist_check_in_test_mode():
    """TEST режим має скипати непозволені сторінки"""
    # Тест тут
    pass
```

### Integration тести

```python
@pytest.mark.asyncio
async def test_bulk_tagging_with_mixed_permissions():
    """Bulk операція з деякими непозволеними сторінками"""
    # TEST: мають бути пропущені
    # SAFE_TEST: мають повернути 403
    # PROD: мають обробитися
    pass
```

---

## Recovery Strategies

### Retry логіка

```python
import asyncio

async def retry_with_backoff(func, max_retries=3, backoff=2):
    for attempt in range(max_retries):
        try:
            return await func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            wait_time = backoff ** attempt
            logger.warning(f"Attempt {attempt+1} failed, retrying in {wait_time}s: {e}")
            await asyncio.sleep(wait_time)
```

### Fallback механізми

```python
def get_mode_safe(default='TEST'):
    """Отримати режим, з fallback на default"""
    try:
        resolver = AgentModeResolver()
        return resolver.get_mode()
    except Exception as e:
        logger.error(f"Failed to get mode: {e}, using default: {default}")
        return default
```

---

## Дивіться також

- [Agent Modes Overview](./agent-modes-overview.md) — огляд режимів
- [Agent Mode Router](./agent-mode-router.md) — маршрутизація
- [Agent Mode Lifecycle](./agent-mode-lifecycle.md) — цикл життя

---

**Версія:** 2.0  
**Дата:** 2025-12-27
