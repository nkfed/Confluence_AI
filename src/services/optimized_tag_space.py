"""
Optimized tag-space pipeline with concurrency, caching, batching, and adaptive throttling.

This module implements:
1. Concurrency limiting via Semaphore
2. Adaptive throttling (adjust concurrency based on 429 errors)
3. Batch processing of pages
4. AI result caching
5. Exponential backoff retries
6. Comprehensive metrics
"""

import asyncio
from typing import Dict, List, Optional
from src.core.logging.logger import get_logger
from src.core.ai.concurrency_manager import get_concurrency_manager
from src.core.ai.caching_layer import get_ai_cache, get_batch_processor
from src.services.tagging_context import prepare_ai_context

logger = get_logger(__name__)
perf_logger = get_logger("tag_space_performance")


class OptimizedTagSpacePipeline:
    """
    Optimized pipeline for tag-space with all optimizations:
    - Concurrency limiting
    - Adaptive throttling
    - Batch processing
    - Caching
    - Exponential backoff
    """
    
    def __init__(self, confluence_client, tagging_agent):
        self.confluence = confluence_client
        self.agent = tagging_agent
        
        # Get shared instances
        self.concurrency = get_concurrency_manager()
        self.cache = get_ai_cache()
        self.batch_processor = get_batch_processor()
        
        # Metrics
        self.metrics = {
            "start_time": None,
            "end_time": None,
            "pages_requested": 0,
            "pages_processed": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "batches_created": 0,
            "ai_calls": 0,
            "errors": 0
        }
    
    async def process_space(
        self,
        page_ids: List[str],
        task_id: str,
        on_progress=None,
        check_stop=None
    ) -> Dict:
        """
        Process all pages in space with optimizations.
        
        Args:
            page_ids: List of page IDs to process
            task_id: Task ID for cancellation
            on_progress: Callback(processed_count, total_count)
            check_stop: Callback() -> bool (returns True if should stop)
        
        Returns:
            Dict with results and metrics
        """
        import time
        start_time = time.time()
        
        # Reset adaptive cooldown counters for new run
        self.concurrency.reset_counters()
        
        self.metrics["start_time"] = start_time
        self.metrics["pages_requested"] = len(page_ids)
        
        logger.info(
            f"[OptimizedTagSpace] Starting pipeline for {len(page_ids)} pages "
            f"(concurrency={self.concurrency.current_concurrency})"
        )
        
        results = []
        errors = 0
        processed = 0
        
        try:
            # Step 1: Fetch page content
            logger.info("[OptimizedTagSpace] Step 1: Fetching page content...")
            pages_data = []
            
            for page_id in page_ids:
                if check_stop and check_stop():
                    logger.info("[OptimizedTagSpace] Stopping due to external request")
                    break
                
                try:
                    page = await self.confluence.get_page(page_id, expand="body.storage")
                    if page:
                        content = page.get("body", {}).get("storage", {}).get("value", "")
                        cleaned_content = prepare_ai_context(content)
                        
                        pages_data.append({
                            "page_id": page_id,
                            "content": cleaned_content,
                            "title": page.get("title", ""),
                            "version": page.get("version", {}).get("number")
                        })
                except Exception as e:
                    logger.error(f"[OptimizedTagSpace] Failed to fetch page {page_id}: {e}")
                    errors += 1
                    results.append({
                        "page_id": page_id,
                        "status": "error",
                        "message": f"Failed to fetch: {str(e)}",
                        "tags": None
                    })
            
            logger.info(f"[OptimizedTagSpace] Fetched {len(pages_data)} pages ({errors} errors)")
            
            # Step 2: Create batches
            logger.info("[OptimizedTagSpace] Step 2: Creating batches...")
            batches = self.batch_processor.create_batches(pages_data)
            self.metrics["batches_created"] = len(batches)
            
            # Step 3: Process batches with concurrency control
            logger.info(f"[OptimizedTagSpace] Step 3: Processing {len(batches)} batches...")
            
            for batch_idx, batch in enumerate(batches, 1):
                if check_stop and check_stop():
                    logger.info("[OptimizedTagSpace] Stopping due to external request")
                    break
                
                logger.debug(f"[OptimizedTagSpace] Processing batch {batch_idx}/{len(batches)} ({len(batch)} pages)")
                
                # Process each page in batch with concurrency limit
                batch_results = await asyncio.gather(
                    *[
                        self._process_single_page_optimized(page, task_id)
                        for page in batch
                    ],
                    return_exceptions=True
                )
                
                for result in batch_results:
                    if isinstance(result, Exception):
                        logger.error(f"[OptimizedTagSpace] Exception in batch: {result}")
                        errors += 1
                    else:
                        results.append(result)
                        processed += 1
                        
                        if on_progress:
                            on_progress(processed, len(pages_data))
                
                # Try to increase concurrency if recovering from 429
                self.concurrency.try_increase_concurrency()
            
            elapsed = time.time() - start_time
            self.metrics["end_time"] = elapsed
            self.metrics["pages_processed"] = processed
            self.metrics["errors"] = errors
            self.metrics["cache_hits"] = self.cache.hits
            self.metrics["cache_misses"] = self.cache.misses
            
            # Log summary
            cache_stats = self.cache.get_stats()
            concurrency_metrics = self.concurrency.get_metrics()
            
            perf_logger.info(
                f"[SUMMARY] Pages: {processed}/{len(pages_data)}, "
                f"Errors: {errors}, "
                f"Time: {elapsed:.1f}s, "
                f"Cache hit rate: {cache_stats['hit_rate']}, "
                f"Rate limits: {concurrency_metrics['rate_limit_errors']}, "
                f"Fallbacks: {concurrency_metrics['fallback_switches']}"
            )
            
            return {
                "results": results,
                "processed": processed,
                "errors": errors,
                "metrics": self.metrics,
                "cache_stats": cache_stats,
                "concurrency_metrics": concurrency_metrics
            }
        
        except Exception as e:
            logger.error(f"[OptimizedTagSpace] Pipeline error: {e}", exc_info=True)
            raise
    
    async def _process_single_page_optimized(self, page_data: Dict, task_id: str) -> Dict:
        """
        Process single page with caching and concurrency control.
        
        Steps:
        1. Check cache
        2. If cache miss: acquire concurrency permit
        3. Call AI with exponential backoff
        4. Cache result
        5. Release permit
        """
        page_id = page_data["page_id"]
        content = page_data["content"]
        
        # Step 1: Check cache
        cached_result = self.cache.get(page_id, content, page_data.get("version"))
        
        if cached_result is not None:
            logger.debug(f"[OptimizedTagSpace] Cache hit for {page_id}")
            self.metrics["cache_hits"] += 1
            return {
                "page_id": page_id,
                "status": "cached",
                "tags": cached_result,
                "from_cache": True
            }
        
        self.metrics["cache_misses"] += 1
        
        # Step 2: Acquire permit and call AI
        try:
            async with asyncio.Semaphore(1):  # Placeholder, real implementation uses concurrency manager
                result = await self.concurrency.call_with_limit(
                    self._call_ai_with_backoff(page_id, content)
                )
            
            # Step 3: Cache result
            self.cache.set(page_id, content, result, page_data.get("version"))
            
            self.metrics["ai_calls"] += 1
            
            return {
                "page_id": page_id,
                "status": "processed",
                "tags": result,
                "from_cache": False
            }
        
        except Exception as e:
            logger.error(f"[OptimizedTagSpace] Failed to process {page_id}: {e}")
            return {
                "page_id": page_id,
                "status": "error",
                "message": str(e),
                "tags": None
            }
    
    async def _call_ai_with_backoff(self, page_id: str, content: str) -> Dict:
        """
        Call AI with exponential backoff.
        
        Backoff sequence: 0.5s, 1s, 2s, 4s (max 3 retries)
        """
        max_retries = 3
        backoff_delays = [0.5, 1.0, 2.0, 4.0]
        
        for attempt in range(max_retries + 1):
            try:
                logger.debug(f"[OptimizedTagSpace] AI call for {page_id} (attempt {attempt + 1})")
                
                # Call agent to suggest tags
                tags = await self.agent.suggest_tags(content)
                
                logger.debug(f"[OptimizedTagSpace] AI success for {page_id}: {tags}")
                return {"proposed": list(tags.values()) if isinstance(tags, dict) else tags, "existing": []}
            
            except Exception as e:
                error_str = str(e)
                is_rate_limit = "429" in error_str
                
                if is_rate_limit:
                    logger.warning(f"[OptimizedTagSpace] 429 Rate limit on {page_id}, attempt {attempt + 1}")
                    self.concurrency.record_rate_limit_error()
                
                if attempt < max_retries:
                    delay = backoff_delays[attempt]
                    logger.info(
                        f"[OptimizedTagSpace] Retry {page_id} in {delay}s "
                        f"(attempt {attempt + 1}/{max_retries})"
                    )
                    self.concurrency.record_retry()
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"[OptimizedTagSpace] Failed {page_id} after {max_retries} retries: {e}")
                    raise
        
        raise RuntimeError(f"Failed to get tags for {page_id}")
