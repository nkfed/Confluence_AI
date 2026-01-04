# Diff Summary — Tag Pages Strict Mode

**File:** src/services/bulk_tagging_service.py
- Use `pages_to_process = unique_page_ids`; no other sources of IDs.
- Whitelist uses `get_entry_points` only; no recursion/child fetch.
- Minimal expand enforced: `get_page(page_id, expand="body.storage")`.
- HTML cleaned/limited via `html_to_text_limited`; metrics logged.
- Allowed calls per page: get_page + get_labels only.

**Tests:** tests/bulk/test_tag_pages_optimized.py
- Updated to mock `get_entry_points` (no recursive whitelist).
- Added mode coverage and minimal-expand assertion.

No other endpoints or shared utilities modified.
