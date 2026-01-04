# Context Centralization Overview (v4.1)
- Global limit via TAGGING_MAX_CONTEXT_CHARS (.env, default 3000).
- Central module: src/services/tagging_context.py → prepare_ai_context().
- Applied to endpoints: tag_pages, tag_tree, tag_space, auto_tag_page.
- Traversal/whitelist logic unchanged; only AI context preparation unified.
