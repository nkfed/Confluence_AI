# Verification — Context Centralization (v4.1)

## Checks
- TAGGING_MAX_CONTEXT_CHARS loaded from .env/settings.
- All tag endpoints call prepare_ai_context (tag_pages, tag_tree, tag_space, auto_tag_page).
- No direct html_to_text or manual truncation in these endpoints.
- Whitelist/traversal logic unchanged.

## Files
- .env, settings.py — new config.
- src/services/tagging_context.py — centralized pipeline.
- src/services/bulk_tagging_service.py — updated endpoints.
- src/services/tagging_service.py — updated auto_tag_page.
- Tests added for context limiting (tag_tree/tag_space and unit).
- Docs updated: TAG_PAGES_ENDPOINT, TAG_TREE_ENDPOINT, BULK_TAGGING_GUIDE, ai_context_flow.

## To Run
```bash
pytest tests/tagging/test_prepare_ai_context.py -v
pytest tests/bulk/test_context_limiting_tree_space.py -v
```
