# Tag-Space Endpoint Documentation (Context v4.1)

## Ендпоінт
```
POST /bulk/tag-space/{space_key}
```

## Centralized AI Context
- Використовує `prepare_ai_context()` (clean → text → trim до TAGGING_MAX_CONTEXT_CHARS з .env).
- Логіка обходу простору та whitelist не змінена.
- Дозволені Confluence виклики на рівні tag-pages: get_page(body.storage), get_labels.

## Whitelist
- Обов'язковий для tag-space; фільтр (джерело сторінок не змінюється).

## Поведінка режимів
- TEST / SAFE_TEST / PROD — незмінно, але контекст підготовки централізовано.

## Приклад
```bash
curl -X POST "http://localhost:8000/bulk/tag-space/DOCS?dry_run=true"
```

## Очікування
- Контекст кожної сторінки ≤ TAGGING_MAX_CONTEXT_CHARS.
- Немає додаткового enrichment; тільки контент сторінки.
