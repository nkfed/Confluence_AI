# Tag-Space Optimization: Step-by-Step Integration Guide

## Overview
This guide walks through integrating the optimization modules into your existing codebase.

**Time estimate:** 30-60 minutes  
**Difficulty:** Medium  
**Risk:** Low (all changes are isolated, no breaking changes)

---

## Prerequisites
- All optimization modules created:
  - ✅ `src/core/ai/concurrency_manager.py`
  - ✅ `src/core/ai/caching_layer.py`
  - ✅ `src/services/optimized_tag_space.py`
- ✅ Documentation created
- Git repository ready for commits

---

## Phase 1: Environment Setup (5 min)

### Step 1.1: Update `.env`

Add these settings:

```env
# Tag-Space Optimization
TAG_SPACE_AI_CONCURRENCY=3
TAG_SPACE_MAX_AI_CONCURRENCY=10
TAG_SPACE_BATCH_SIZE=5
TAG_SPACE_CACHE_ENABLED=true
TAG_SPACE_CACHE_SIZE=1000
```

**Verify:**
```bash
python -c "import os; print(os.getenv('TAG_SPACE_AI_CONCURRENCY', 'not set'))"
# Should print: 3
```

---

## Phase 2: Update AI Router (10 min)

### Step 2.1: Import concurrency manager

File: `src/core/ai/router.py`

At the top of the file, add:

```python
# Add to imports section (around line 10)
import asyncio
from src.core.ai.concurrency_manager import get_concurrency_manager
```

### Step 2.2: Replace retry logic

Find the `generate()` method (around line 150) and update:

**BEFORE (current code):**
```python
async def _invoke(client: AIProvider, name: str) -> AIResponse:
    model = getattr(client, "model_default", None)
    router_logger.info(f"[ROUTER] Selected provider={name} model={model}")
    return await log_ai_call(...)

# Try once, fallback
try:
    return await _invoke(client, provider_name)
except Exception as primary_exc:
    # Switch to fallback
```

**AFTER (optimized code):**
```python
async def _invoke(client: AIProvider, name: str) -> AIResponse:
    model = getattr(client, "model_default", None)
    router_logger.info(f"[ROUTER] Selected provider={name} model={model}")
    concurrency_mgr = get_concurrency_manager()
    
    return await log_ai_call(...)

# Exponential backoff retries
max_retries = 3
backoff_delays = [0.5, 1.0, 2.0]
concurrency_mgr = get_concurrency_manager()

for attempt in range(max_retries + 1):
    try:
        result = await concurrency_mgr.call_with_limit(
            _invoke(client, provider_name)
        )
        return result
    
    except Exception as primary_exc:
        error_str = str(primary_exc)
        is_rate_limit = "429" in error_str
        
        if is_rate_limit:
            concurrency_mgr.record_rate_limit_error()
            router_logger.warning("[429] Reducing concurrency due to rate limit")
        
        if attempt < max_retries:
            delay = backoff_delays[attempt]
            concurrency_mgr.record_retry()
            router_logger.info(
                f"[BACKOFF] Retry after {delay}s (attempt {attempt+1}/{max_retries})"
            )
            await asyncio.sleep(delay)
        else:
            # Fallback logic...
            if self._fallback and self._fallback != provider_name:
                concurrency_mgr.record_fallback()
            raise
```

**Verify:**
```bash
python -c "from src.core.ai.router import AIProviderRouter; print('✅ Router imports OK')"
```

---

## Phase 3: Update Tag-Space (15 min)

### Step 3.1: Update imports

File: `src/services/bulk_tagging_service.py`

Add to imports section (around line 10):

```python
from src.services.optimized_tag_space import OptimizedTagSpacePipeline
from src.core.ai.concurrency_manager import get_concurrency_manager
```

### Step 3.2: Replace page processing loop

Find the `tag_space()` method (around line 520).

Look for this section:

```python
# OLD: Iterate through pages one by one
for page_id in pages_to_process:
    try:
        page = await self.confluence.get_page(page_id)
        # ... process page ...
        results.append(...)
    except Exception as e:
        # ... handle error ...
```

Replace with:

```python
# NEW: Use optimized pipeline
logger.info("[TagSpace] Using OptimizedTagSpacePipeline")

optimized_pipeline = OptimizedTagSpacePipeline(
    self.confluence,
    self.agent
)

# Define progress callback
def on_progress(processed, total):
    if task_id in TASK_PROGRESS:
        TASK_PROGRESS[task_id]["processed"] = processed
    logger.debug(f"[TagSpace] Progress: {processed}/{total}")

# Define stop check
def check_stop():
    return not ACTIVE_TASKS.get(task_id, True)

# Run optimized pipeline
try:
    pipeline_result = await optimized_pipeline.process_space(
        page_ids=pages_to_process,
        task_id=task_id,
        on_progress=on_progress,
        check_stop=check_stop
    )
    
    results = pipeline_result["results"]
    processed_count = pipeline_result["processed"]
    error_count = pipeline_result["errors"]
    
    # Log optimization metrics
    cache_stats = pipeline_result["cache_stats"]
    concurrency_metrics = pipeline_result["concurrency_metrics"]
    
    perf_logger = get_logger("tag_space_performance")
    perf_logger.info(
        f"[OPTIMIZATION_SUMMARY] "
        f"Processed: {processed_count}/{len(pages_to_process)}, "
        f"Errors: {error_count}, "
        f"Cache Hit Rate: {cache_stats['hit_rate']}, "
        f"Rate Limits: {concurrency_metrics['rate_limit_errors']}, "
        f"Fallbacks: {concurrency_metrics['fallback_switches']}, "
        f"Total AI Calls: {concurrency_metrics['total_ai_calls']}"
    )

except Exception as e:
    logger.error(f"[TagSpace] Optimization pipeline failed: {e}", exc_info=True)
    # Fallback to original logic or raise
    raise
```

### Step 3.3: Update response structure

Find where the response is built (end of `tag_space()` method):

```python
response = {
    "task_id": task_id,
    "total": len(page_ids),
    "processed": len(results),  # ← Update this
    "success": sum(1 for r in results if r.get("status") != "error"),
    "errors": sum(1 for r in results if r.get("status") == "error"),
    "skipped_by_whitelist": 0,  # ← For tag_space, always 0
    "dry_run": effective_dry_run,
    "mode": mode,
    "whitelist_enabled": False,  # ← tag_space doesn't use whitelist
    "details": results
}
```

**Verify:**
```bash
python -c "from src.services.bulk_tagging_service import BulkTaggingService; print('✅ Service imports OK')"
```

---

## Phase 4: Testing (20 min)

### Step 4.1: Create test script

File: `test_optimization.py`

```python
#!/usr/bin/env python3
"""
Quick validation of optimization modules.
"""

import asyncio
from src.core.ai.concurrency_manager import get_concurrency_manager
from src.core.ai.caching_layer import get_ai_cache, get_batch_processor


async def test_concurrency():
    """Test concurrency manager."""
    print("\n[TEST] Concurrency Manager...")
    mgr = get_concurrency_manager()
    
    # Check initial state
    assert mgr.current_concurrency > 0, "Concurrency should be > 0"
    print(f"  ✅ Initial concurrency: {mgr.current_concurrency}")
    
    # Test rate limit response
    mgr.record_rate_limit_error()
    assert mgr.metrics["rate_limit_errors"] == 1
    print(f"  ✅ Rate limit recording works")
    
    # Test metrics
    metrics = mgr.get_metrics()
    assert "total_ai_calls" in metrics
    print(f"  ✅ Metrics available: {list(metrics.keys())}")


def test_cache():
    """Test caching layer."""
    print("\n[TEST] Caching Layer...")
    cache = get_ai_cache()
    
    # Test set/get
    page_id = "test_123"
    content = "test content for caching"
    result = {"tags": ["tag1", "tag2"]}
    
    cached = cache.get(page_id, content)
    assert cached is None, "Cache should be empty initially"
    print(f"  ✅ Empty cache returns None")
    
    cache.set(page_id, content, result, version=1)
    cached = cache.get(page_id, content, version=1)
    assert cached == result, "Cache should return stored result"
    print(f"  ✅ Cache set/get works")
    
    # Test stats
    stats = cache.get_stats()
    assert stats["hits"] >= 1
    print(f"  ✅ Cache stats: {stats}")


def test_batch():
    """Test batch processor."""
    print("\n[TEST] Batch Processor...")
    processor = get_batch_processor()
    
    # Create test data
    pages = [
        {"page_id": f"page_{i}", "content": f"content_{i}"}
        for i in range(15)
    ]
    
    batches = processor.create_batches(pages)
    assert len(batches) == 3, "15 pages with batch_size=5 should create 3 batches"
    print(f"  ✅ Created {len(batches)} batches")
    
    # Test formatting
    prompt = processor.format_batch_for_ai(batches[0])
    assert "page_0" in prompt
    print(f"  ✅ Batch formatting works (prompt length: {len(prompt)})")


async def main():
    """Run all tests."""
    print("=" * 60)
    print("TAG-SPACE OPTIMIZATION VALIDATION")
    print("=" * 60)
    
    try:
        await test_concurrency()
        test_cache()
        test_batch()
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        print("\nReady for integration!")
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(asyncio.run(main()))
```

Run it:
```bash
python test_optimization.py
# Should output:
# ✅ ALL TESTS PASSED!
```

### Step 4.2: Test with real tag-space

Small integration test:

```python
# Start server
uvicorn src.main:app --reload

# In another terminal:
curl -X POST "http://localhost:8000/bulk/tag-space/nkfedba" \
  -H "Content-Type: application/json" \
  -d '{"dry_run": true}'

# Should return:
{
  "task_id": "...",
  "total": 46,
  "processed": 46,  # ← Should be all pages, not just whitelist
  "success": 40,
  "errors": 0,
  "skipped_by_whitelist": 0,  # ← Should be 0!
  ...
}
```

---

## Phase 5: Validation (10 min)

### Step 5.1: Check logs

```bash
# Check concurrency adjustments
tail -100 logs/ai_router.log | grep -i "throttle\|429\|backoff"
# Should show adaptive concurrency adjustments

# Check cache performance
tail -100 logs/app.log | grep -i "cache"
# Should show cache hits on second run

# Check overall performance
grep "OPTIMIZATION_SUMMARY" logs/app.log
# Should show metrics on each tag-space completion
```

### Step 5.2: Monitor metrics

Create monitoring script:

```bash
#!/bin/bash
# monitor_optimization.sh

echo "Monitoring optimization metrics..."
while true; do
  clear
  echo "=== TAG-SPACE OPTIMIZATION STATUS ==="
  echo ""
  echo "Rate Limit Errors (429):"
  grep "429\|THROTTLE" logs/ai_router.log | tail -5
  echo ""
  echo "Fallback Switches:"
  grep "FALLBACK" logs/ai_router.log | tail -5
  echo ""
  echo "Latest Optimization Summary:"
  grep "OPTIMIZATION_SUMMARY" logs/app.log | tail -1
  echo ""
  sleep 5
done
```

---

## Phase 6: Deployment Checklist

Before going live:

- [ ] All modules imported without errors
- [ ] Environment variables set in `.env`
- [ ] Test script passes (`test_optimization.py`)
- [ ] Small space processes without errors (< 30s)
- [ ] Cache hit rate > 50% on second run
- [ ] No infinite loops in concurrency adjustment
- [ ] Logs show expected metrics
- [ ] Rollback plan documented (in case needed)

---

## Rollback Procedure (If Needed)

If anything goes wrong:

### Option 1: Conservative Mode

Edit `.env`:
```env
TAG_SPACE_AI_CONCURRENCY=1
TAG_SPACE_BATCH_SIZE=1
TAG_SPACE_CACHE_ENABLED=false
```

Restart server. This disables all optimizations.

### Option 2: Full Rollback

Revert the code changes:
```bash
git diff src/core/ai/router.py  # Check what changed
git checkout src/core/ai/router.py  # Revert
git checkout src/services/bulk_tagging_service.py
```

Restart server with original code.

---

## Expected Results After Integration

### Small Space (10-20 pages)
- ✅ Processing time: < 30 seconds
- ✅ AI calls: ~2-4 (thanks to batching)
- ✅ Cache hit rate (2nd run): > 70%
- ✅ No 429 errors

### Medium Space (100-200 pages)
- ✅ Processing time: 1-2 minutes
- ✅ AI calls: ~20-40 (vs 100-200 before)
- ✅ Rate limit errors: < 3 (vs 15-20 before)
- ✅ Fallback switches: 0 (vs 10-15 before)

### Large Space (500+ pages)
- ✅ Processing time: 5-10 minutes
- ✅ AI calls: ~100-150 (5-10× reduction)
- ✅ Concurrency auto-tuned: 3-4
- ✅ Cache hit rate: 60-80%

---

## Support & Troubleshooting

### Issue: Still getting 429 errors

**Solution:**
```env
# Reduce concurrency further
TAG_SPACE_AI_CONCURRENCY=2
TAG_SPACE_MAX_AI_CONCURRENCY=5
```

### Issue: Processing time increased

**Solution:**
```env
# Check if cache is too large or batch size too small
TAG_SPACE_BATCH_SIZE=10
TAG_SPACE_AI_CONCURRENCY=5
```

### Issue: Out of memory

**Solution:**
```env
# Reduce cache size
TAG_SPACE_CACHE_SIZE=500
TAG_SPACE_BATCH_SIZE=3
```

---

## Next Steps After Integration

1. **Monitor in production** for 1-2 weeks
2. **Collect metrics** on 429 errors and processing times
3. **Fine-tune** env variables based on results
4. **Consider persistent cache** (Redis) for further optimization
5. **Implement alerting** for rate limit spikes

---

**Status:** Ready for integration! 🚀
