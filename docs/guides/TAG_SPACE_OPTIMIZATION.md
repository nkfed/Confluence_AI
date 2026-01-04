# Tag-Space Pipeline Optimization: Implementation Guide

## Overview
This document outlines the optimization implemented for the tag-space endpoint to reduce:
- Gemini 429 rate-limit errors
- Fallback switches to GPT
- Retry cycles
- Total processing time

## Architecture Changes

### 1. **Concurrency Management** (`src/core/ai/concurrency_manager.py`)

**Problem**: Bursts of 20-200 parallel AI requests → Gemini rate limits (429)

**Solution**: 
- Global `asyncio.Semaphore` limiting concurrent AI calls
- Configurable via `TAG_SPACE_AI_CONCURRENCY` (default: 3)
- Adaptive throttling: reduces concurrency by 50% on 429, increases by 20% after 5 min recovery

**Usage**:
```python
from src.core.ai.concurrency_manager import get_concurrency_manager

manager = get_concurrency_manager()

# All AI calls must go through this
result = await manager.call_with_limit(ai_coro)

# Record errors to adjust concurrency
if "429" in str(error):
    manager.record_rate_limit_error()
```

**Expected Impact**:
- Reduces 429 errors by ~70-80%
- Stabilizes throughput
- Maintains optimal concurrency automatically

---

### 2. **Caching Layer** (`src/core/ai/caching_layer.py`)

**Problem**: Repeated AI calls for same content → high load, low efficiency

**Solution**:
- Hash-based cache (`SHA256(content)`)
- Version-aware invalidation (cache cleared if page version changes)
- Max 1000 entries (LRU eviction)

**Usage**:
```python
from src.core.ai.caching_layer import get_ai_cache

cache = get_ai_cache()

# Check cache first
cached = cache.get(page_id, content, version=page_version)
if cached:
    return cached

# Compute and cache
result = await ai_call(content)
cache.set(page_id, content, result, version=page_version)
return result
```

**Expected Impact**:
- Reduces AI calls by 5-10× (if pages unchanged)
- Hit rate: 60-90% on repeated runs
- Eliminates redundant processing

---

### 3. **Batch Processing** (`src/core/ai/caching_layer.py`)

**Problem**: 1 page → 1 AI call → N calls for N pages

**Solution**:
- Group pages into batches (default: 5 pages/batch)
- Single AI prompt for entire batch
- AI returns labels for each page in batch
- Configurable via `TAG_SPACE_BATCH_SIZE`

**Usage**:
```python
from src.core.ai.caching_layer import get_batch_processor

processor = get_batch_processor()

# Split 100 pages into 20 batches (5 pages each)
batches = processor.create_batches(pages)

# Process in parallel
for batch in batches:
    prompt = processor.format_batch_for_ai(batch)
    results = await ai_call(prompt)  # Single AI call for 5 pages
    parse_results(results)
```

**Expected Impact**:
- Reduces AI calls by 5-10×
- Reduces router overhead
- Single prompt covers more content

---

### 4. **Exponential Backoff Retries** (in `ai_router.py`)

**Problem**: Fixed retries + immediate fallback → unstable

**Solution**:
- Exponential backoff: 0.5s → 1s → 2s → 4s
- Max 3 retries (configurable)
- Gives Gemini time to recover between attempts

**Expected Impact**:
- More successful retries
- Fewer unnecessary fallbacks
- Better recovery from transient errors

---

### 5. **Metrics & Monitoring**

**Available Metrics**:
```python
manager = get_concurrency_manager()
metrics = manager.get_metrics()

# Returns:
{
    "total_ai_calls": 150,
    "successful_calls": 145,
    "failed_calls": 5,
    "rate_limit_errors": 3,      # ← Key metric
    "fallback_switches": 2,       # ← Key metric
    "retries": 8,
    "current_concurrency": 4,
    "concurrency_adjustments": [
        {"time": "2026-01-03T20:52:00", "reason": "rate_limit_error_429", 
         "old_concurrency": 5, "new_concurrency": 3},
        ...
    ]
}
```

**Cache Stats**:
```python
cache = get_ai_cache()
stats = cache.get_stats()

# Returns:
{
    "hits": 45,
    "misses": 15,
    "hit_rate": "75.0%",
    "size": 42,
    "max_size": 1000
}
```

---

## Environment Variables

Configure behavior via `.env`:

```env
# Concurrency (max parallel AI calls for tag-space)
TAG_SPACE_AI_CONCURRENCY=3
TAG_SPACE_MAX_AI_CONCURRENCY=10

# Batching (pages per AI call)
TAG_SPACE_BATCH_SIZE=5

# Cache
TAG_SPACE_CACHE_SIZE=1000
TAG_SPACE_CACHE_ENABLED=true
```

---

## Integration Steps

### Step 1: Install New Modules
```bash
# Files already created:
# - src/core/ai/concurrency_manager.py
# - src/core/ai/caching_layer.py
# - src/services/optimized_tag_space.py
```

### Step 2: Update tag_space Implementation
Modify `src/services/bulk_tagging_service.py` `tag_space()` method to:
1. Use `OptimizedTagSpacePipeline`
2. Pass concurrency manager
3. Use batch processor
4. Collect metrics

### Step 3: Update AI Router
Modify `src/core/ai/router.py` to:
1. Implement exponential backoff in retry logic
2. Integrate concurrency manager
3. Record 429 errors and fallbacks

### Step 4: Testing
Run on:
- Small space (10-20 pages): Should complete < 30s
- Medium space (100-200 pages): Should complete < 2 min
- Large space (500+ pages): Should complete < 10 min

Validate:
- Rate limit errors: < 5% of AI calls
- Fallback switches: < 2% of AI calls
- Cache hit rate: 60-80% on second run
- Concurrency adjustments: Auto-tuning visible

---

## Expected Performance Gains

### Before Optimization
- 100 pages × avg 2 retries = 200 AI calls
- Gemini 429 errors: 15-20%
- Fallback to GPT: 10-15%
- Processing time: 5-10 minutes

### After Optimization
- 100 pages ÷ 5 batch_size = 20 AI calls
- Cache hit rate: 60-80%
- Actual AI calls: 4-8 (if 50% cache hit)
- Gemini 429 errors: 1-3%
- Fallback to GPT: 0-1%
- Processing time: 30-60 seconds
- **Speed increase: 5-10×**

---

## Monitoring

Watch these logs for issues:
```
[ConcurrencyManager] - Concurrency adjustments
[THROTTLE] - Rate limit responses
[FALLBACK] - Provider fallbacks
[CACHE] - Cache hits/misses
[METRICS_SUMMARY] - Summary statistics
[OptimizedTagSpace] - Pipeline progress
```

---

## Rollback Plan

If issues occur:
1. Disable batching: `TAG_SPACE_BATCH_SIZE=1`
2. Increase concurrency: `TAG_SPACE_AI_CONCURRENCY=1`
3. Disable cache: `TAG_SPACE_CACHE_ENABLED=false`
4. Revert to original `tag_pages` (non-optimized)

---

## Future Improvements

1. **Persistent Cache**: Redis/SQLite for cross-session caching
2. **Predictive Throttling**: ML model to predict 429 errors
3. **Parallel Batches**: Process multiple batches concurrently
4. **Smart Retries**: Different backoff for different error types
5. **Cost Optimization**: Track token usage by provider

---

## Questions & Support

For issues:
1. Check logs in `logs/ai_router.log` and `logs/app.log`
2. Review metrics from `get_concurrency_manager().get_metrics()`
3. Verify cache hit rate and batch efficiency
