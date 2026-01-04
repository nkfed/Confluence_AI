# Tests for Tag Pages Strict Mode

## Test list (tag-pages only)
1) test_only_page_ids_processed — ensures only request IDs processed.
2) test_no_enrichment_calls — bans children/ancestors/related/space/incoming.
3) test_minimal_expand_enforced — get_page uses expand="body.storage" only.
4) test_context_minimization_html_cleaning — scripts/styles/macros removed.
5) test_context_limitation_text_truncation — AI context ≤3000 chars.
6) test_context_metrics_calculation — metrics computed.
7) test_whitelist_filtering_for_tag_pages — whitelist acts as filter only.
8) test_strict_mode_across_modes — strict sourcing in TEST/SAFE_TEST/PROD.
9) test_dry_run_no_updates — dry_run blocks updates.
10) test_tag_pages_performance (slow) — optional performance smoke.

## How to run
```bash
pytest tests/bulk/test_tag_pages_optimized.py -v
```

## Notes
- Mocks whitelist entry points only (no recursion).
- Counts of get_page/get_labels must equal number of request.page_ids.
- No other Confluence methods should be invoked in these tests.
