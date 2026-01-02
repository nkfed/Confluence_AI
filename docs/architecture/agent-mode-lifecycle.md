# Agent Mode Lifecycle

Цикл життя агентів у системі агент-режимів.

## Етапи Execution Flow

```
1. Request отримується
   ↓
2. AgentModeResolver визначає режим (TEST/SAFE_TEST/PROD)
   ↓
3. Whitelist перевіряється (TEST/SAFE_TEST обов., PROD skip)
   ↓
4. Dry-run прапор встановлюється
   ↓
5. Агент виконує операцію
   ↓
6. Результат форматується за режимом
   ↓
7. Response повертається
```

---

## Деталі по етапам

### 1. Request отримується

Запит приходить до FastAPI endpoint-а:

```python
@router.post("/bulk/tag-space/{space_key}")
async def tag_space(
    space_key: str,
    request: TagSpaceRequest,
):
    # Request готовий до обробки
```

### 2. Визначення режиму

AgentModeResolver визначає режим з `AGENT_MODE` env variable:

```python
from src.core.agent_mode_resolver import AgentModeResolver

resolver = AgentModeResolver()
mode = resolver.get_mode()  # 'TEST' | 'SAFE_TEST' | 'PROD'
```

**Правила:**
- TEST: Абсолютно безпечний, без змін
- SAFE_TEST: Напів-безпечний, зміни тільки для whitelist
- PROD: Повний доступ, без обмежень

### 3. Whitelist перевірка

```python
if mode in ['TEST', 'SAFE_TEST']:
    allowed_ids = await whitelist_manager.get_allowed_ids(
        space_key, 
        confluence_client
    )
    
    for page_id in request.page_ids:
        if page_id not in allowed_ids:
            if mode == 'TEST':
                skip(page_id)  # TEST скипує
            else:
                raise PermissionError()  # SAFE_TEST блокує
else:  # PROD
    # Whitelist ігнорується
    pass
```

### 4. Встановлення Dry-Run

```python
if mode == 'TEST':
    dry_run = True  # Force dry-run
elif mode == 'SAFE_TEST':
    dry_run = request.dry_run  # Використовуй параметр
else:  # PROD
    dry_run = request.dry_run  # Використовуй параметр
```

### 5. Виконання операції

Агент виконується з заданим режимом:

```python
from src.agents.tagging_agent import TaggingAgent

agent = TaggingAgent()
result = await agent.tag_page(
    page_id=page_id,
    space_key=space_key,
    dry_run=dry_run,
    # ... інші параметри
)
```

### 6. Форматування результату

```python
if dry_run:
    response = {
        "status": "dry_run",
        "message": "Simulation only, no changes made",
        "affected_pages": [...],
        "would_remove": [...],
        "would_add": [...]
    }
else:
    response = {
        "status": "updated",
        "message": "Changes applied",
        "affected_pages": [...],
        "removed_tags": [...],
        "added_tags": [...]
    }
```

### 7. Response повертається

```python
return {
    "summary": {...},
    "details": [...],
    "mode": mode,
    "timestamp": datetime.now()
}
```

---

## State Diagram

```
┌─────────────┐
│   REQUEST   │
└──────┬──────┘
       │
       ▼
┌──────────────────┐
│ Determine Mode   │
│ TEST|SAFE_TEST   │     (Decision Point)
│ PROD             │
└──────┬───────────┘
       │
       ├─── TEST ─────────────────────┐
       │                               │
       ├─── SAFE_TEST ────┐           │
       │                  │           │
       └─── PROD ──────┐  │           │
                       │  │           │
                       ▼  ▼           ▼
                  ┌──────────────────────────┐
                  │  Check Whitelist?        │
                  │  (TEST/SAFE_TEST only)   │
                  └──────┬───────────────────┘
                         │
                    ┌────┴────┐
                    │          │
                   YES        NO
                    │          │
                    ▼          ▼
              ┌─────────┐  ┌─────────┐
              │ ALLOWED │  │  BLOCK  │
              └────┬────┘  └────┬────┘
                   │            │
                   ▼            ▼
            ┌────────────────────────┐
            │ Set dry_run flag       │
            │ (mode dependent)       │
            └────────┬───────────────┘
                     │
                     ▼
            ┌────────────────────────┐
            │ Execute Agent/Service  │
            │ with mode & dry_run    │
            └────────┬───────────────┘
                     │
                     ▼
            ┌────────────────────────┐
            │ Format Response        │
            │ based on dry_run       │
            └────────┬───────────────┘
                     │
                     ▼
            ┌────────────────────────┐
            │ Return Response        │
            └────────────────────────┘
```

---

## Дивіться також

- [Agent Modes Overview](./agent-modes-overview.md) — огляд режимів
- [Agent Mode Router](./agent-mode-router.md) — маршрутизація
- [Agent Mode Error Handling](./agent-mode-errors.md) — обробка помилок

---

**Версія:** 2.0  
**Дата:** 2025-12-27
