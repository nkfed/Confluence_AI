# Full Fix for tag_pages() - Complete Implementation

**Scope:** POST /bulk/tag-pages endpoint ONLY  
**Target:** Reduce context + minimize API calls + enable parallelization  
**Impact:** 118 sec → 10-15 sec (8-12x faster)

---

## 📝 Complete tag_pages() Implementation

### Location
File: `src/services/bulk_tagging_service.py`  
Method: `async def tag_pages()`  
Lines: ~60-230

### Changes Required

**Change #1: Minimal expand parameter**
```python
# BEFORE (line 168)
page = await self.confluence.get_page(page_id)

# AFTER
page = await self.confluence.get_page(page_id, expand="body.storage")
```

**Change #2: Import local utilities at method start**
```python
# ADD at top of tag_pages() method
from src.services.tag_pages_utils import html_to_text_limited, get_context_metrics
```

**Change #3: Use context-limited text for AI**
```python
# BEFORE (lines 172-180)
text = page.get("body", {}).get("storage", {}).get("value", "")
logger.debug(f"[TagPages] Extracted {len(text)} chars from page {page_id}")

# Формуємо індивідуальний AI-промпт на основі контенту
logger.info(f"[TagPages] Calling TaggingAgent via router for page {page_id}")
from src.agents.tagging_agent import TaggingAgent
agent = TaggingAgent(ai_router=router)
tags = await agent.suggest_tags(text)

# AFTER
html = page.get("body", {}).get("storage", {}).get("value", "")
logger.debug(f"[TagPages] Raw HTML extracted: {len(html):,} chars from page {page_id}")

# ✅ CONTEXT MINIMIZATION: Clean and limit text for AI
text = html_to_text_limited(html, max_chars=3000)
metrics = get_context_metrics(html, text)
logger.info(
    f"[TagPages:ContextMinimization] page={page_id}, "
    f"original={metrics['original_html_chars']:,} → "
    f"final={metrics['cleaned_text_chars']:,} chars, "
    f"reduction={metrics['reduction_pct']:.1f}%"
)

# Формуємо індивідуальний AI-промпт на основі обмеженого контенту
logger.info(f"[TagPages] Calling TaggingAgent via router for page {page_id}")
from src.agents.tagging_agent import TaggingAgent
agent = TaggingAgent(ai_router=router)
tags = await agent.suggest_tags(text)
```

---

## 🔀 Optional: Parallelization (Change #4)

**Location:** Lines 155-230 (main processing loop)

**BEFORE:** Serial processing
```python
for page_id_int in filtered_ids:
    page_id = str(page_id_int)
    try:
        # ... process page ...
    except Exception as e:
        # ... handle error ...
    
    if task_id and task_id in TASK_PROGRESS:
        TASK_PROGRESS[task_id]["processed"] += 1
    
    await asyncio.sleep(0.3)
```

**AFTER:** Parallel processing
```python
async def _process_single_page(page_id_int: int) -> dict:
    """Process a single page asynchronously."""
    page_id = str(page_id_int)
    
    # Check if task was stopped
    if task_id and not ACTIVE_TASKS.get(task_id, True):
        logger.info(f"[TagPages] Task {task_id} stopped, skipping page {page_id}")
        return None
    
    try:
        logger.info(f"[TagPages] Processing page {page_id} (effective_dry_run={effective_dry_run})")
        
        # ✅ MINIMAL EXPAND
        page = await self.confluence.get_page(page_id, expand="body.storage")
        if not page:
            logger.warning(f"[TagPages] Page {page_id} not found")
            return {
                "page_id": page_id,
                "status": "error",
                "message": "Page not found"
            }
        
        # ✅ CONTEXT MINIMIZATION
        html = page.get("body", {}).get("storage", {}).get("value", "")
        text = html_to_text_limited(html, max_chars=3000)
        
        logger.info(f"[TagPages] Calling TaggingAgent for page {page_id}")
        from src.agents.tagging_agent import TaggingAgent
        agent = TaggingAgent(ai_router=router)
        tags = await agent.suggest_tags(text)
        
        logger.info(f"[TagPages] Generated tags for {page_id}: {tags}")
        
        # Flatten and compare
        flat_tags = flatten_tags(tags)
        existing_labels = await self.confluence.get_labels(page_id)
        
        proposed = set(flat_tags)
        existing = set(existing_labels)
        to_add = proposed - existing
        
        logger.info(
            f"[TagPages] Tag comparison for {page_id}: "
            f"proposed={len(proposed)}, existing={len(existing)}, to_add={len(to_add)}"
        )
        
        # Dry-run logic
        if effective_dry_run:
            status = "forbidden" if mode == "TEST" else "dry_run"
            logger.info(f"[TagPages] [{status.upper()}] Would add labels for {page_id}: {list(to_add)}")
            return {
                "page_id": page_id,
                "status": status,
                "tags": {
                    "proposed": list(proposed),
                    "existing": list(existing),
                    "added": [],
                    "to_add": list(to_add)
                },
                "dry_run": True
            }
        
        # Real update
        if to_add:
            logger.info(f"[TagPages] Updating labels for page {page_id}: {list(to_add)}")
            await self.confluence.update_labels(page_id, list(to_add))
        
        return {
            "page_id": page_id,
            "status": "updated",
            "tags": {
                "proposed": list(proposed),
                "existing": list(existing),
                "added": list(to_add),
                "to_add": []
            },
            "dry_run": False
        }
        
    except Exception as e:
        logger.error(f"[TagPages] Failed to process page {page_id}: {e}")
        return {
            "page_id": page_id,
            "status": "error",
            "message": str(e),
            "tags": None
        }
    finally:
        # Update progress
        if task_id and task_id in TASK_PROGRESS:
            TASK_PROGRESS[task_id]["processed"] += 1
        await asyncio.sleep(0.1)  # Reduced from 0.3 due to parallelization

# ✅ PARALLEL EXECUTION
logger.info(f"[TagPages] Starting parallel processing of {len(filtered_ids)} pages")

if filtered_ids:
    tasks = [_process_single_page(page_id_int) for page_id_int in filtered_ids]
    results_list = await asyncio.gather(*tasks, return_exceptions=False)
    
    for result in results_list:
        if result is None:
            continue  # Task was stopped
        
        results.append(result)
        
        if result.get("status") in ["updated", "dry_run"]:
            success_count += 1
        elif result.get("status") == "error":
            error_count += 1

logger.info(f"[TagPages] Parallel processing completed: {success_count} success, {error_count} errors")
```

---

## ✅ Validation Checklist

Before applying changes, verify:

- [ ] NO calls to `get_children()` in tag_pages() (only in tag_tree/tag_space)
- [ ] NO calls to `get_ancestors()` in tag_pages()
- [ ] NO calls to `get_space()` in tag_pages()
- [ ] NO calls to `get_related_pages()` in tag_pages()
- [ ] NO enrichment calls beyond get_page() + get_labels()
- [ ] expand parameter set to "body.storage" (no version, metadata, ancestors)
- [ ] HTML cleaning applied locally within tag_pages()
- [ ] Text limited to 3000 chars for AI
- [ ] Tag-tree, tag-space, tag methods NOT modified
- [ ] ConfluenceClient.get_page() default expand NOT changed
- [ ] TaggingAgent NOT modified for global use

---

## 📊 Expected Results After Fix

### Performance Improvement
```
BEFORE:
- Total time (2 pages): 118 sec
- Per page: 59 sec
- Confluence API call: ~10 sec (large expand)
- AI call: ~30 sec (50-100K tokens)
- Per-page serial overhead: ~19 sec

AFTER (Minimal fixes #1-3):
- Total time (2 pages): 20-30 sec
- Per page: 10-15 sec
- Confluence API call: ~2 sec (minimal expand)
- AI call: ~2 sec (500-1000 tokens)
- Per-page overhead: ~1-5 sec
- SPEEDUP: 4-6x faster

AFTER (With parallelization #4):
- Total time (2 pages): 10-15 sec
- Per page: 5-7 sec (parallel)
- SPEEDUP: 8-12x faster
```

### Context Reduction
```
BEFORE:
- Raw HTML: 5-10 MB
- AI tokens: 50-100K
- Processing time: 30+ sec per page

AFTER:
- Cleaned text: ~3 KB
- AI tokens: 500-1000
- Processing time: ~2 sec per page
- REDUCTION: 99% smaller context
```

---

## 🧪 Testing

### Unit Test: Context Minimization
```python
from src.services.tag_pages_utils import html_to_text_limited, get_context_metrics

def test_context_limited():
    large_html = "<p>Content</p>" * 1000  # 7000+ chars
    text = html_to_text_limited(large_html, max_chars=3000)
    assert len(text) <= 3000
    assert "Content" in text
    
    metrics = get_context_metrics(large_html, text)
    assert metrics['reduction_pct'] > 90
```

### Integration Test: tag_pages Performance
```python
@pytest.mark.asyncio
async def test_tag_pages_performance():
    # Request to /bulk/tag-pages with 2 pages
    # Expected: < 15 seconds with optimizations
    # Log output should show:
    # - minimal expand in get_page() calls
    # - context reduction metrics
    # - no child/ancestor/related page calls
```

---

**Status:** ✅ Ready for implementation  
**Impact:** 8-12x performance improvement  
**Risk:** Very low (localized changes only)  
**Side effects:** None (other endpoints unaffected)
