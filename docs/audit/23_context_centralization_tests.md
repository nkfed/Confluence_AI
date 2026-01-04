# Tests — Context Centralization

New/updated tests:
- tests/tagging/test_prepare_ai_context.py
  - test_html_cleaning_removes_noise
  - test_text_limiting_defaults_to_env
  - test_prepare_ai_context_trims
- tests/bulk/test_context_limiting_tree_space.py
  - test_context_limiting_applies_to_tag_tree
  - test_context_limiting_applies_to_tag_space
- Existing tag-pages tests use centralized context implicitly.

Run:
```bash
pytest tests/tagging/test_prepare_ai_context.py -v
pytest tests/bulk/test_context_limiting_tree_space.py -v
```
