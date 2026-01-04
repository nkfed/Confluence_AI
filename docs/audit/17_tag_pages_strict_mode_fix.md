# Tag Pages Strict Mode Fix

**Date:** 2 January 2026  
**Scope:** POST /bulk/tag-pages only  

## What changed
- tag_pages now processes **only** request.page_ids (deduped) as `pages_to_process`.
- Whitelist is used **only as a filter**, not as a source of additional IDs (entry points only, no recursion, no child fetch).
- Allowed Confluence calls inside tag_pages: `get_page(page_id, expand="body.storage")`, `get_labels(page_id)`.
- HTML context is cleaned and limited to 3000 chars via `html_to_text_limited` (local util); context reduction logged.
- No enrichment, no recursion, no tree traversal, no extra expand fields.

## Files touched
- src/services/bulk_tagging_service.py — strict mode logic, minimal expand, context limiting.
- tests/bulk/test_tag_pages_optimized.py — strict-mode tests and minimal expand checks.

## Expected behavior
- Only explicit page_ids are fetched, filtered by whitelist, and sent to AI.
- No additional Confluence requests beyond the two allowed per page.
- Works identically across TEST / SAFE_TEST / PROD regarding strict sourcing.
