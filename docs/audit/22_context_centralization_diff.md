# Diff Summary — Context Centralization
- Added TAGGING_MAX_CONTEXT_CHARS env/config in .env and settings.py.
- New module: src/services/tagging_context.py (clean → text → trim + metrics).
- tag_pages/tag_tree/tag_space/auto_tag_page now call prepare_ai_context.
- Removed direct html_to_text usage and manual truncation in these endpoints.
- Tests updated/added for context limiting.
