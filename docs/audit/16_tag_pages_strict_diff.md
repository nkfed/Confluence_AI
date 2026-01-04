# Diff – Strict Mode for POST /bulk/tag-pages

**File:** src/services/bulk_tagging_service.py  
**Method:** tag_pages()

```diff
@@
-        # ✅ Remove duplicates while preserving order
-        unique_page_ids = list(dict.fromkeys(page_ids))
-        duplicates_removed = len(page_ids) - len(unique_page_ids)
-
-        if duplicates_removed > 0:
-            logger.info(f"[TagPages] Removed {duplicates_removed} duplicate page_ids")
-
-        page_ids = unique_page_ids
+        # ✅ Strict mode: process only explicitly provided page_ids (no other sources)
+        unique_page_ids = list(dict.fromkeys(page_ids))
+        duplicates_removed = len(page_ids) - len(unique_page_ids)
+        if duplicates_removed > 0:
+            logger.info(f"[TagPages] Removed {duplicates_removed} duplicate page_ids")
+
+        pages_to_process = unique_page_ids  # do not append children/ancestors/related pages
@@
-        page_ids_int = [int(pid) for pid in page_ids]
+        page_ids_int = [int(pid) for pid in pages_to_process]
@@
-        skipped_due_to_whitelist = len(page_ids) - len(filtered_ids)
+        skipped_due_to_whitelist = len(pages_to_process) - len(filtered_ids)
@@
-                # Завантажуємо контент сторінки
-                page = await self.confluence.get_page(page_id)
+                # Завантажуємо контент сторінки (мінімальний expand)
+                page = await self.confluence.get_page(page_id, expand="body.storage")
@@
-            "total": len(page_ids),
+            "total": len(pages_to_process),
```

**Net effect:**
- Processing strictly limited to request.page_ids (deduped).
- No additional sources of page IDs are introduced.
- Confluence calls limited to get_page(body.storage) and get_labels.
- tag-tree/tag-space/other endpoints remain unchanged.
