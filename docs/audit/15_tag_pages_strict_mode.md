# Strict Mode: POST /bulk/tag-pages

**Date:** 2 January 2026  
**Scope:** tag_pages() method ONLY  
**Goal:** Guarantee processing strictly the request.page_ids list without any tree traversal or enrichment.

---

## ✅ Final Behavior
- Pages to process = request.page_ids (deduped only).
- For each page_id:
  1) `get_page(page_id, expand="body.storage")`
  2) `get_labels(page_id)`
  3) `TaggingAgent.suggest_tags(text)`
- No additional Confluence calls (no children/ancestors/related/space/metadata/version beyond body.storage).
- Whitelist filtering still applies, but does not add new pages.

---

## 🔒 Explicitly Disabled
- `get_children()`, `get_descendants()`, `get_ancestors()`
- `get_space()`, `get_related_pages()`, `get_incoming_links()`
- Any recursion or tree traversal
- Any additional expand fields (version, metadata, ancestors, space)
- Any enrichment or context expansion beyond `body.storage`

---

## 🔧 Code Changes (tag_pages only)
1) Enforce strict page source
- Introduced `pages_to_process = unique_page_ids` with no other sources.
- All counters now use `pages_to_process` (not any other collection).

2) Minimal expand on page fetch
- `get_page(page_id, expand="body.storage")` replaces default expand.

3) No structural changes elsewhere
- tag-tree, tag-space, other endpoints remain untouched.
- ConfluenceClient defaults unchanged.
- TaggingAgent unchanged globally.

---

## 🎯 Acceptance Criteria
- Only request.page_ids are processed (after dedupe and whitelist filter).
- No extra Confluence calls besides get_page + get_labels.
- No enrichment/metadata/version/ancestors/children requests.
- Behavior confined strictly to tag_pages().
