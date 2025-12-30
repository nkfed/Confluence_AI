# Changelog

## [Unreleased]

### ✨ Added - 2025-12-30

#### 🌲 Reset Tags with Tree Scope Support (`root_id` parameter)

**Feature:** Extended `POST /bulk/reset-tags/{space_key}` endpoint with `root_id` parameter for tree-scoped tag removal.

**What's New:**
- ➕ New optional query parameter `root_id` for targeting specific page trees
- ➕ Automatic validation that `root_id` belongs to the specified `space_key`
- ➕ New response fields: `scope` (`"space"` | `"tree"`) and `root_id`
- ➕ Two new service methods:
  - `TagResetService.collect_tree_pages()` — recursive tree collection
  - `TagResetService.reset_tree_tags()` — tree-scoped tag reset

**Usage Examples:**
```bash
# Reset all AI tags in entire space (space scope)
POST /bulk/reset-tags/MYSPACE?dry_run=false

# Reset all AI tags in page tree (tree scope)
POST /bulk/reset-tags/MYSPACE?root_id=123456&dry_run=false

# Reset specific categories in tree
POST /bulk/reset-tags/MYSPACE?root_id=123456&categories=doc,kb&dry_run=false
```

**Response Format:**
```json
{
  "scope": "tree",
  "root_id": "123456",
  "total": 15,
  "processed": 15,
  "removed": 12,
  "no_tags": 3,
  "errors": 0,
  "dry_run": false,
  "details": [...]
}
```

**Files Changed:**
- `src/api/routers/bulk_reset_tags.py` — added root_id parameter and validation
- `src/services/tag_reset_service.py` — added tree collection and reset methods

**Tests:**
- ✅ 7 new test cases in `tests/test_reset_tags_root_id.py`
- ✅ All tests passing (7/7)

**Documentation:**
- 📖 Full API documentation: `docs/RESET_TAGS_ROOT_ID.md`
- 📝 Implementation summary: `docs/RESET_TAGS_ROOT_ID_SUMMARY.md`
- 🎯 Demo script: `tests/demo_reset_tags_root_id.py`

**Related Issues:**
- Consistent with `tag-tree` architecture and logic
- Uses same recursive tree traversal approach
- Compatible with existing `categories` and `dry_run` parameters

### 🔧 Fixed - 2025-12-30

#### 🔍 Added `expand` parameter support to `ConfluenceClient.get_page()`

**Issue:** `get_page()` method didn't support `expand` parameter, causing errors when `root_id` validation tried to fetch page space information.

**Fix:** Updated `get_page()` method signature to accept optional `expand` parameter:
- Default value: `"body.storage,version"` (maintains backward compatibility)
- Supports custom values: `"space"`, `""` (no expand), or comma-separated combinations
- Only adds `?expand=` to URL if expand is not empty

**Examples:**
```python
# Default behavior (unchanged)
page = await client.get_page("123456")  # expand=body.storage,version

# Get space information
page = await client.get_page("123456", expand="space")

# Minimal data (no expand)
page = await client.get_page("123456", expand="")

# Multiple parameters
page = await client.get_page("123456", expand="space,version,body.storage")
```

**Files Changed:**
- `src/clients/confluence_client.py` — updated `get_page()` method signature

**Tests:**
- ✅ 6 new test cases in `tests/test_confluence_client_expand.py`
- ✅ All existing tests still passing (backward compatibility verified)
- ✅ Total: 22/22 tests passing

**Documentation:**
- 📖 Fix details: `docs/EXPAND_PARAMETER_FIX.md`

**Impact:**
- ✅ Backward compatible — all existing calls work without changes
- ✅ Enables `reset-tags` with `root_id` validation
- ✅ More flexible API for future use cases

### 🔧 Changed - 2025-12-30

#### 📊 Standardized dry_run response structure for `reset-tags`

**Issue:** Previous implementation incorrectly showed `removed > 0` even in dry_run mode, and used `removed_tags` field for tags that weren't actually removed.

**Changes:**

**dry_run=true (simulation):**
- Root fields:
  - `removed`: Always `0` (no actual removal)
  - `to_remove`: Number of pages that would be processed
- Details fields:
  - `to_remove_tags`: Tags that would be removed (was `removed_tags`)
  - `status`: `"dry_run"`

**dry_run=false (actual removal):**
- Root fields:
  - `removed`: Actual number of pages processed
  - `to_remove`: Not included
- Details fields:
  - `removed_tags`: Actually removed tags
  - `status`: `"removed"`

**Examples:**

Dry-run response:
```json
{
  "removed": 0,
  "to_remove": 5,
  "dry_run": true,
  "details": [
    {
      "status": "dry_run",
      "to_remove_tags": ["doc-api", "kb-guide"]
    }
  ]
}
```

Actual removal response:
```json
{
  "removed": 5,
  "dry_run": false,
  "details": [
    {
      "status": "removed",
      "removed_tags": ["doc-api", "kb-guide"]
    }
  ]
}
```

**Files Changed:**
- `src/services/tag_reset_service.py` — updated response structure logic

**Tests:**
- ✅ 3 new test cases for dry_run vs actual removal
- ✅ Updated 13 existing tests
- ✅ Total: 25/25 tests passing

**Documentation:**
- 📖 Response structure guide: `docs/DRY_RUN_RESPONSE_STANDARD.md`

**Benefits:**
- ✅ Clear distinction between simulation and actual removal
- ✅ Prevents confusion with `removed=0` in dry_run mode
- ✅ Informative `to_remove` field shows what will happen
- ✅ Follows API best practices for dry_run modes

---

## [Previous Versions]

*(Add previous changelog entries here)*

---

## Legend

- ✨ Added — new features
- 🔧 Changed — changes in existing functionality
- 🐛 Fixed — bug fixes
- 🗑️ Deprecated — soon-to-be removed features
- ❌ Removed — removed features
- 🔒 Security — security fixes
