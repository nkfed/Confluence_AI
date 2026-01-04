"""
Concurrency and throttling manager for AI calls in tag-space pipeline.

Features:
- Global async semaphore for rate limiting
- Adaptive throttling (auto-adjust concurrency based on 429 errors)
- Exponential backoff for retries
- Metrics collection
"""

import asyncio
import os
from datetime import datetime, timedelta
from typing import Optional
from src.core.logging.logger import get_logger

logger = get_logger(__name__)
metrics_logger = get_logger("ai_concurrency_metrics")


class ConcurrencyManager:
    """
    Manages concurrent AI calls with adaptive throttling.
    
    Features:
    - Limits concurrent AI calls via asyncio.Semaphore
    - Adjusts concurrency dynamically based on rate-limit errors
    - Tracks metrics for monitoring
    """
    
    def __init__(self):
        # Configuration
        self.min_concurrency = 1
        self.max_concurrency = int(os.getenv("TAG_SPACE_MAX_AI_CONCURRENCY", "10"))
        self.initial_concurrency = int(os.getenv("TAG_SPACE_AI_CONCURRENCY", "3"))
        
        # Current state
        self.current_concurrency = self.initial_concurrency
        self.semaphore = asyncio.Semaphore(self.current_concurrency)
        
        # Metrics
        self.metrics = {
            "total_ai_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "rate_limit_errors": 0,
            "fallback_switches": 0,
            "retries": 0,
            "last_429_time": None,
            "concurrency_adjustments": []
        }
        
        # Adaptive throttling
        self.last_rate_limit_time = None
        self.recovery_check_interval = timedelta(minutes=5)  # Check every 5 min
        
        # Adaptive cooldown counters
        self.success_counter = 0
        self.rate_limit_counter = 0
        
        logger.info(
            f"[ConcurrencyManager] Initialized: "
            f"initial_concurrency={self.initial_concurrency}, "
            f"max_concurrency={self.max_concurrency}"
        )
    
    async def acquire(self):
        """Acquire a permit to execute an AI call."""
        await self.semaphore.acquire()
    
    def release(self):
        """Release a permit."""
        self.semaphore.release()
    
    async def call_with_limit(self, coro):
        """Execute a coroutine with concurrency limit."""
        async with self.semaphore:
            self.metrics["total_ai_calls"] += 1
            try:
                result = await coro
                self.metrics["successful_calls"] += 1
                
                # Adaptive cooldown: pause after 12 successful Gemini calls
                self.success_counter += 1
                self.rate_limit_counter = 0  # Reset on success
                
                if self.success_counter >= 12:
                    logger.info("[COOLDOWN] 12 successful Gemini calls reached — pausing 5 seconds")
                    await asyncio.sleep(5)
                    self.success_counter = 0
                
                return result
            except Exception as e:
                self.metrics["failed_calls"] += 1
                raise
    
    async def record_rate_limit_error(self):
        """Record a 429 rate-limit error and adjust concurrency."""
        self.metrics["rate_limit_errors"] += 1
        self.last_rate_limit_time = datetime.utcnow()
        self.rate_limit_counter += 1
        
        # Adaptive cooldown: pause after 3 consecutive 429 errors
        if self.rate_limit_counter >= 3:
            logger.warning("[COOLDOWN] 3 consecutive 429 errors — pausing 10 seconds")
            await asyncio.sleep(10)
            self.rate_limit_counter = 0
        
        # Reduce concurrency by 50% (minimum 1)
        new_concurrency = max(self.min_concurrency, self.current_concurrency // 2)
        
        if new_concurrency != self.current_concurrency:
            old_concurrency = self.current_concurrency
            self.current_concurrency = new_concurrency
            
            # Recreate semaphore with new limit
            self.semaphore = asyncio.Semaphore(self.current_concurrency)
            
            adjustment = {
                "time": datetime.utcnow().isoformat(),
                "reason": "rate_limit_error_429",
                "old_concurrency": old_concurrency,
                "new_concurrency": new_concurrency
            }
            self.metrics["concurrency_adjustments"].append(adjustment)
            
            metrics_logger.warning(
                f"[THROTTLE] 429 Rate Limit: reducing concurrency {old_concurrency} → {new_concurrency}"
            )
    
    def try_increase_concurrency(self):
        """
        Try to increase concurrency if 5 minutes have passed without 429 errors.
        """
        if self.last_rate_limit_time is None:
            return  # Never had a 429
        
        time_since_last_429 = datetime.utcnow() - self.last_rate_limit_time
        
        if time_since_last_429 >= self.recovery_check_interval:
            # No 429 for 5 minutes, try to increase concurrency
            new_concurrency = min(
                self.max_concurrency,
                int(self.current_concurrency * 1.2)  # Increase by 20%
            )
            
            if new_concurrency > self.current_concurrency:
                old_concurrency = self.current_concurrency
                self.current_concurrency = new_concurrency
                
                # Recreate semaphore
                self.semaphore = asyncio.Semaphore(self.current_concurrency)
                
                adjustment = {
                    "time": datetime.utcnow().isoformat(),
                    "reason": "recovery_after_429",
                    "old_concurrency": old_concurrency,
                    "new_concurrency": new_concurrency
                }
                self.metrics["concurrency_adjustments"].append(adjustment)
                
                metrics_logger.info(
                    f"[THROTTLE] Recovery: increasing concurrency {old_concurrency} → {new_concurrency}"
                )
    
    def record_fallback(self):
        """Record a fallback to alternative provider."""
        self.metrics["fallback_switches"] += 1
        metrics_logger.warning(f"[FALLBACK] Fallback to alternative provider (total: {self.metrics['fallback_switches']})")
    
    def record_retry(self):
        """Record a retry attempt."""
        self.metrics["retries"] += 1
    
    def get_metrics(self) -> dict:
        """Get current metrics."""
        return {
            **self.metrics,
            "current_concurrency": self.current_concurrency,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def log_metrics_summary(self):
        """Log a summary of metrics."""
        m = self.metrics
        metrics_logger.info(
            f"[METRICS_SUMMARY] "
            f"total_calls={m['total_ai_calls']}, "
            f"successful={m['successful_calls']}, "
            f"failed={m['failed_calls']}, "
            f"rate_limits={m['rate_limit_errors']}, "
            f"fallbacks={m['fallback_switches']}, "
            f"retries={m['retries']}, "
            f"current_concurrency={self.current_concurrency}"
        )
    
    def reset_counters(self):
        """Reset adaptive cooldown counters at start of each run."""
        self.success_counter = 0
        self.rate_limit_counter = 0
        logger.info("[ConcurrencyManager] Counters reset for new tag-space run")


# Global instance
_concurrency_manager: Optional[ConcurrencyManager] = None


def get_concurrency_manager() -> ConcurrencyManager:
    """Get or create the global concurrency manager."""
    global _concurrency_manager
    if _concurrency_manager is None:
        _concurrency_manager = ConcurrencyManager()
    return _concurrency_manager
