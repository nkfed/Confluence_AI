# Implementation Patches for Tag-Space Optimization

## File 1: src/core/ai/router.py
### Change 1: Add exponential backoff to retry logic

Replace the retry logic in `generate()` method with exponential backoff:

```python
# OLD CODE (around line 200):
async def _invoke(client: AIProvider, name: str) -> AIResponse:
    model = getattr(client, "model_default", None)
    router_logger.info(f"[ROUTER] Selected provider={name} model={model}")
    return await log_ai_call(
        provider_name=name,
        model=model,
        operation="router.generate",
        coro=lambda: client.generate(prompt, **kwargs)
    )

# PRIMARY ATTEMPT WITH EXPONENTIAL BACKOFF
max_retries = 3
backoff_delays = [0.5, 1.0, 2.0, 4.0]

for attempt in range(max_retries + 1):
    try:
        return await _invoke(client, provider_name)
    except Exception as primary_exc:
        if attempt < max_retries:
            delay = backoff_delays[attempt]
            router_logger.info(
                f"[RETRY] Provider={provider_name}, attempt={attempt + 1}, "
                f"delay={delay}s, error={primary_exc}"
            )
            await asyncio.sleep(delay)
        else:
            # All retries exhausted, try fallback if available
            ...

# NEW CODE:
# Import at top
import asyncio
from src.core.ai.concurrency_manager import get_concurrency_manager

async def _invoke(client: AIProvider, name: str) -> AIResponse:
    model = getattr(client, "model_default", None)
    router_logger.info(f"[ROUTER] Selected provider={name} model={model}")
    
    concurrency_mgr = get_concurrency_manager()
    
    return await log_ai_call(
        provider_name=name,
        model=model,
        operation="router.generate",
        coro=lambda: client.generate(prompt, **kwargs)
    )

# Exponential backoff retry logic
max_retries = 3
backoff_delays = [0.5, 1.0, 2.0]

for attempt in range(max_retries + 1):
    try:
        concurrency_mgr = get_concurrency_manager()
        return await concurrency_mgr.call_with_limit(_invoke(client, provider_name))
    
    except Exception as primary_exc:
        error_str = str(primary_exc)
        is_rate_limit = "429" in error_str
        
        if is_rate_limit:
            concurrency_mgr.record_rate_limit_error()
            router_logger.warning(f"[429] Gemini rate limit detected, reducing concurrency")
        
        if attempt < max_retries:
            delay = backoff_delays[attempt]
            concurrency_mgr.record_retry()
            router_logger.info(
                f"[BACKOFF] Provider={provider_name}, attempt={attempt + 1}, "
                f"backoff={delay}s (rate_limit={is_rate_limit})"
            )
            await asyncio.sleep(delay)
        else:
            # Fallback logic...
            if self._fallback and self._fallback != provider_name:
                concurrency_mgr.record_fallback()
                router_logger.warning(f"[FALLBACK] Switching to {self._fallback}")
            raise
```

---

## File 2: src/services/bulk_tagging_service.py
### Change 1: Integrate OptimizedTagSpacePipeline into tag_space()

Replace the page processing loop in `tag_space()` with:

```python
# At top of tag_space method, add imports:
from src.services.optimized_tag_space import OptimizedTagSpacePipeline
from src.core.ai.concurrency_manager import get_concurrency_manager

# Create optimized pipeline
optimized_pipeline = OptimizedTagSpacePipeline(self.confluence, self.agent)

# Process with optimization
def on_progress(processed, total):
    if task_id in TASK_PROGRESS:
        TASK_PROGRESS[task_id]["processed"] = processed

def check_stop():
    return not ACTIVE_TASKS.get(task_id, True)

pipeline_result = await optimized_pipeline.process_space(
    page_ids=pages_to_process,
    task_id=task_id,
    on_progress=on_progress,
    check_stop=check_stop
)

# Extract results
results = pipeline_result["results"]
concurrency_metrics = pipeline_result["concurrency_metrics"]

# Log metrics
perf_logger = get_logger("tag_space_performance")
perf_logger.info(
    f"[TAG_SPACE_OPTIMIZATION] "
    f"Pages: {pipeline_result['processed']}/{pipeline_result['pages_requested']}, "
    f"Cache hit rate: {pipeline_result['cache_stats']['hit_rate']}, "
    f"Rate limits: {concurrency_metrics['rate_limit_errors']}, "
    f"Fallbacks: {concurrency_metrics['fallback_switches']}"
)
```

---

## File 3: Environment Configuration (.env)

Add these settings:

```env
# Tag-Space Optimization
TAG_SPACE_AI_CONCURRENCY=3
TAG_SPACE_MAX_AI_CONCURRENCY=10
TAG_SPACE_BATCH_SIZE=5
TAG_SPACE_CACHE_ENABLED=true
TAG_SPACE_CACHE_SIZE=1000
```

---

## Testing Checklist

Before deployment, verify:

- [ ] Small space (10 pages): < 30s
- [ ] Medium space (100 pages): < 2 min
- [ ] Rate limit errors: < 5%
- [ ] Fallback switches: < 2%
- [ ] Cache hit rate (2nd run): > 60%
- [ ] Logs show concurrency adjustments
- [ ] No timeout errors

---

## Monitoring Queries

After deployment, check:

```bash
# Check rate limit frequency
grep "429" logs/ai_router.log | wc -l

# Check fallback frequency
grep "FALLBACK" logs/ai_router.log | wc -l

# Check concurrency adjustments
grep "THROTTLE\|Recovery" logs/ai_router.log

# Check cache performance
grep "CACHE" logs/ai_concurrency_metrics.log | tail -20
```

---

## Expected Metrics After Optimization

```
[METRICS_SUMMARY]
total_calls=20 (down from 100)
successful=19
failed=1
rate_limits=0-1 (down from 15-20)
fallbacks=0 (down from 10-15)
retries=2-3 (structured, with backoff)
current_concurrency=3-4 (auto-tuned)
processing_time=45s (down from 300s)
cache_hit_rate=65% (on 2nd run)
```

---

## Rollback Procedure

If issues occur:

1. Set `TAG_SPACE_BATCH_SIZE=1` to disable batching
2. Set `TAG_SPACE_AI_CONCURRENCY=1` to disable concurrency
3. Set `TAG_SPACE_CACHE_ENABLED=false` to disable cache
4. Restart service
5. Test with small space
6. Debug from logs

---
