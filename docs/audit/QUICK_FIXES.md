# Quick Fixes for Post-Refactor Issues

## 🚨 Priority 1: Fix 3 Active Doc Issues (2 min)

### Issue 1: Remove archived references from INDEX.md

**Location:** [docs/INDEX.md](../INDEX.md)

**Fix 1a:** Remove UNIFIED_BULK_ARCHITECTURE.md reference (around line 52)
```diff
- | **[architecture/UNIFIED_BULK_ARCHITECTURE.md](architecture/UNIFIED_BULK_ARCHITECTURE.md)** | Уніфікована архітектура bulk операцій |
```

**Fix 1b:** Remove SPACES_METADATA_SUMMARY.md reference (around line 80)
```diff
- | **[spaces/SPACES_METADATA_SUMMARY.md](spaces/SPACES_METADATA_SUMMARY.md)** | Summary для spaces |
```

### Issue 2: Fix path in SPACES_METADATA_FILTERING.md

**Location:** [docs/spaces/SPACES_METADATA_FILTERING.md](../spaces/SPACES_METADATA_FILTERING.md)

**Fix:** In "Related Files" section, change:
```diff
- [TAG_PAGES_ENDPOINT.md](TAG_PAGES_ENDPOINT.md)
+ [TAG_PAGES_ENDPOINT.md](../bulk-operations/TAG_PAGES_ENDPOINT.md)
```

---

## ✨ Optional: Add deprecation notes to audit files

### Files to update:
- `docs/audit/02_duplicates_analysis.md`
- `docs/audit/03_terms_consistency.md`
- `docs/audit/04_broken_links.md`
- `docs/audit/06_structure_v4.md`

**Add at top:**
```markdown
⚠️ **Note:** This audit file documents old file structures and names.
After v4.0 restructuring, files were reorganized and some archived.
See [07_merge_report.md](07_merge_report.md) and [07_post_refactor_link_check.md](07_post_refactor_link_check.md) for details.

---
```

---

## 🔗 Verify all fixes

After applying fixes, run:
```bash
cd d:/Projects/Confluence_AI
.venv/Scripts/python.exe docs/audit/_tmp_linkcheck.py
```

**Expected result:** ~64 problems (down from 93)
- 27 in archive/ (acceptable)
- 52 in audit/ (acceptable)
- 0 in active docs ✅

---

## 📝 Commands to apply fixes (copy-paste ready)

```bash
# 1. Remove UNIFIED_BULK_ARCHITECTURE reference from INDEX.md
# Find this line around line 52:
# | **[architecture/UNIFIED_BULK_ARCHITECTURE.md](architecture/UNIFIED_BULK_ARCHITECTURE.md)** | Уніфікована архітектура bulk операцій |
# Delete it entirely

# 2. Remove SPACES_METADATA_SUMMARY reference from INDEX.md  
# Find this line around line 80:
# | **[spaces/SPACES_METADATA_SUMMARY.md](spaces/SPACES_METADATA_SUMMARY.md)** | Summary для spaces |
# Delete it entirely

# 3. Fix SPACES_METADATA_FILTERING.md
# Find in "Related Files" section:
# - [TAG_PAGES_ENDPOINT.md](TAG_PAGES_ENDPOINT.md)
# Replace with:
# - [TAG_PAGES_ENDPOINT.md](../bulk-operations/TAG_PAGES_ENDPOINT.md)
```

---

**Estimated time to fix:** 2-3 minutes  
**Complexity:** Low - simple deletions and path fix  
**Priority:** HIGH - needed for v4.0 release readiness

