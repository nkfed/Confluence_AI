# Verification Checklist — Tag Pages Strict Mode

## Functional
- [ ] Only request.page_ids processed (deduped).
- [ ] Whitelist acts as filter only (entry points, no recursion).
- [ ] Per-page calls: get_page(expand="body.storage"), get_labels.
- [ ] No calls to children/ancestors/related/space/incoming.
- [ ] No enrichment/recursion/tree traversal.

## Modes
- [ ] TEST: strict sourcing honored.
- [ ] SAFE_TEST: strict sourcing honored.
- [ ] PROD: strict sourcing honored (whitelist filter skipped only if design allows).

## Context
- [ ] HTML cleaned (scripts/styles/iframe/ac:macro removed, attrs stripped).
- [ ] Text limited to 3000 chars for AI.
- [ ] Context reduction logged per page.

## Tests
- [ ] pytest tests/bulk/test_tag_pages_optimized.py -v
- [ ] get_page calls == N (page_ids), get_labels == N

## CI Guards (to add)
- [ ] Block usage in tag_pages of: get_child_pages, get_descendants, get_ancestors, get_space, get_related_pages, get_incoming_links, expand="body.storage,version".
- [ ] Snapshot: get_page N times, get_labels N times.

## Docs
- [ ] TAG_PAGES_ENDPOINT.md updated with strict-mode rules.
- [ ] Bulk tagging guide updated (differences vs tag-tree/tag-space).
- [ ] whitelist.md reflects filter-only behavior for tag_pages.
- [ ] Changelog entry for v4.1 strict mode.

## Ready to release
- [ ] All checks above green.
