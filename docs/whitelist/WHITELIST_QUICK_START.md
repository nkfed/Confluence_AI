# Whitelist Mechanism - Quick Start

## 🚀 Швидкий старт

### 1. Додати простір у whitelist

Відредагуйте `src/core/whitelist/whitelist_config.json`:

```json
{
  "spaces": [
    {
      "space_key": "YOUR_SPACE_KEY",
      "description": "My documentation space",
      "pages": [
        {
          "id": 123456,
          "name": "Main documentation root",
          "root": true
        },
        {
          "id": 789012,
          "name": "Subsection entry point",
          "root": false
        }
      ]
    }
  ]
}
```

### 2. Запустити tag-space

```bash
curl -X POST "http://localhost:8000/bulk/tag-space/YOUR_SPACE_KEY"
```

### 3. Перевірити результат

У відповіді буде інформація про whitelist:

```json
{
  "mode": "TEST",
  "whitelist_enabled": true,
  "skipped_by_whitelist": 50,
  "processed": 25
}
```

## 📝 Типові сценарії

### Додати root + entry points

```json
{
  "id": 100,
  "name": "Documentation root",
  "root": true
}
```
→ Обробляється ВСЯ піддеревна структура

### Додати тільки entry points (без root)

```json
{
  "id": 200,
  "name": "Section A",
  "root": false
},
{
  "id": 300,
  "name": "Section B",
  "root": false
}
```
→ Обробляються тільки ці сторінки + їх дочірні

### PROD режим

Змініть `.env`:
```env
AGENT_MODE=PROD
```

→ Whitelist ігнорується, обробляються ВСІ сторінки

## 🔧 Налагодження

### Перевірити валідацію

```python
from src.core.whitelist import WhitelistManager

manager = WhitelistManager()
warnings = manager.validate()

if warnings:
    for w in warnings:
        print(f"⚠️ {w}")
```

### Перевірити allowed_ids

```python
allowed_ids = await manager.get_allowed_ids("YOUR_SPACE_KEY", confluence_client)
print(f"Allowed pages: {len(allowed_ids)}")
print(allowed_ids)
```

### Очистити кеш

```python
manager.clear_cache()
```

## 📚 Детальна документація

Дивіться [WHITELIST_MECHANISM.md](./WHITELIST_MECHANISM.md)
