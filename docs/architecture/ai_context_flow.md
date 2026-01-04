# Centralized AI Context Preparation (v4.1)

- Applies to: tag-pages, tag-tree, tag-space, auto_tag_page (tag-single).
- Steps:
  1. Clean HTML (scripts/styles/iframe/ac:macro/attrs removed).
  2. Convert to text.
  3. Trim to TAGGING_MAX_CONTEXT_CHARS (from .env, default 3000).
  4. Log metrics (original, cleaned, final length).
- Entry point: `src/services/tagging_context.py` → `prepare_ai_context()`.
- Only context preparation changes; traversal/whitelist logic unchanged.
