"""
Optimization Patch v2.0 for Gemini AI calls.

Implements:
1. Pre-flight rate control (check recent call history before calling)
2. Adaptive cooldown (wait based on consecutive 429 errors)
3. Micro-batching (process 2 items at a time)
4. Improved fallback with detailed metrics
"""

import asyncio
import time
from collections import deque
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from src.core.logging.logger import get_logger

logger = get_logger(__name__)


@dataclass
class CallMetrics:
    """Metrics for a single AI call."""
    provider: str  # 'gemini' or 'openai'
    success: bool
    tokens: Optional[int] = None
    duration_ms: float = 0.0
    fallback_reason: Optional[str] = None  # 429, 500, 503, client_error, unknown
    cooldown_reason: Optional[str] = None  # normal, preflight, rate_limit, adaptive
    cooldown_ms: float = 0.0
    timestamp: float = field(default_factory=time.time)


class OptimizationPatchV2:
    """
    Optimization Patch v2: Adaptive cooldown + Pre-flight + Micro-batching
    
    Features:
    - Pre-flight rate control: checks recent call history before making request
    - Adaptive cooldown: escalating wait times based on consecutive 429s
    - Micro-batching: processes items in batches of 2
    - Detailed metrics collection for analysis
    """
    
    def __init__(self):
        # Recent call tracking (last 20 calls)
        self.recent_calls: deque = deque(maxlen=20)
        
        # 429 error tracking
        self.last_429_time: float = 0.0
        self.consecutive_429: int = 0
        
        # Metrics
        self.call_metrics: List[CallMetrics] = []
        self.cooldown_histogram: Dict[str, int] = {
            "normal": 0,
            "preflight": 0,
            "rate_limit": 0,
            "adaptive": 0,
        }
        
        logger.info("[OptimizationPatchV2] Initialized")
    
    def now(self) -> float:
        """Get current time in milliseconds."""
        return time.time() * 1000
    
    async def preflight_cooldown(self) -> tuple[bool, str, float]:
        """
        Pre-flight rate control: check if we should wait before calling.
        
        Rules:
        1. If 429 was received <3000ms ago → wait 1500ms
        2. If >=2 calls in last 2000ms → wait 1000ms
        3. Otherwise → no wait (or minimal 500ms)
        
        Returns:
            (should_wait, reason, wait_ms)
        """
        t = self.now()
        
        # Rule 1: Recent 429 error
        if t - self.last_429_time < 3000:
            logger.debug("[Preflight] Recent 429 detected (<3s), waiting 1500ms")
            await asyncio.sleep(1.5)
            return True, "preflight_recent_429", 1500
        
        # Rule 2: Too many recent calls
        recent_calls = [ts for ts in self.recent_calls if t - ts < 2000]
        if len(recent_calls) >= 2:
            logger.debug(f"[Preflight] {len(recent_calls)} calls in last 2s, waiting 1000ms")
            await asyncio.sleep(1.0)
            return True, "preflight_rate_limit", 1000
        
        # No wait needed
        return False, "preflight_none", 0
    
    async def adaptive_cooldown(self) -> tuple[str, float]:
        """
        Adaptive cooldown: escalating wait times based on consecutive 429s.
        
        Levels:
        - 0 consecutive: 500ms
        - 1 consecutive: 1500ms
        - 2 consecutive: 3000ms
        - 3+ consecutive: 7000ms
        
        Returns:
            (reason, wait_ms)
        """
        c = self.consecutive_429
        
        if c == 0:
            await asyncio.sleep(0.5)
            return "adaptive_none", 500
        elif c == 1:
            logger.warning(f"[Adaptive] 1 consecutive 429, waiting 1500ms")
            await asyncio.sleep(1.5)
            return "adaptive_1x429", 1500
        elif c == 2:
            logger.warning(f"[Adaptive] 2 consecutive 429, waiting 3000ms")
            await asyncio.sleep(3.0)
            return "adaptive_2x429", 3000
        else:  # c >= 3
            logger.error(f"[Adaptive] {c} consecutive 429s, waiting 7000ms")
            await asyncio.sleep(7.0)
            return "adaptive_3plus_429", 7000
    
    def micro_batch(self, items: List[Any]) -> List[List[Any]]:
        """
        Split items into micro-batches of 2 items each.
        
        Example:
        - [1, 2, 3, 4, 5] → [[1, 2], [3, 4], [5]]
        
        Args:
            items: List of items to batch
            
        Returns:
            List of micro-batches (each batch size <= 2)
        """
        if len(items) <= 2:
            return [items]
        
        batches = []
        for i in range(0, len(items), 2):
            batches.append(items[i:i+2])
        
        logger.debug(f"[MicroBatch] Split {len(items)} items into {len(batches)} batches of ~2")
        return batches
    
    async def record_call(
        self,
        provider: str,
        success: bool,
        tokens: Optional[int] = None,
        duration_ms: float = 0,
        fallback_reason: Optional[str] = None,
        cooldown_reason: Optional[str] = None,
        cooldown_ms: float = 0,
    ):
        """Record metrics for a single AI call."""
        metrics = CallMetrics(
            provider=provider,
            success=success,
            tokens=tokens,
            duration_ms=duration_ms,
            fallback_reason=fallback_reason,
            cooldown_reason=cooldown_reason,
            cooldown_ms=cooldown_ms,
        )
        
        self.call_metrics.append(metrics)
        
        # Track recent calls
        if success:
            self.recent_calls.append(self.now())
        
        # Update cooldown histogram
        if cooldown_reason:
            self.cooldown_histogram[cooldown_reason] = self.cooldown_histogram.get(cooldown_reason, 0) + 1
    
    def record_429(self):
        """Record a 429 error and update state."""
        self.last_429_time = self.now()
        self.consecutive_429 += 1
    
    def reset_consecutive_429(self):
        """Reset consecutive 429 counter on successful call."""
        self.consecutive_429 = 0
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive statistics about all recorded calls."""
        if not self.call_metrics:
            return {
                "total_calls": 0,
                "gemini_success_rate": 0,
                "fallback_rate": 0,
                "cooldown_histogram": self.cooldown_histogram,
            }
        
        total = len(self.call_metrics)
        gemini_calls = [m for m in self.call_metrics if m.provider == "gemini"]
        openai_calls = [m for m in self.call_metrics if m.provider == "openai"]
        
        gemini_success = len([m for m in gemini_calls if m.success])
        gemini_rate = (gemini_success / len(gemini_calls) * 100) if gemini_calls else 0
        fallback_rate = (len(openai_calls) / total * 100) if total > 0 else 0
        
        avg_duration = sum(m.duration_ms for m in self.call_metrics) / total if total > 0 else 0
        total_tokens = sum(m.tokens or 0 for m in self.call_metrics)
        
        fallback_reasons = {}
        for m in openai_calls:
            if m.fallback_reason:
                fallback_reasons[m.fallback_reason] = fallback_reasons.get(m.fallback_reason, 0) + 1
        
        return {
            "total_calls": total,
            "gemini_calls": len(gemini_calls),
            "gemini_success": gemini_success,
            "gemini_success_rate": f"{gemini_rate:.1f}%",
            "fallback_calls": len(openai_calls),
            "fallback_rate": f"{fallback_rate:.1f}%",
            "avg_duration_ms": f"{avg_duration:.1f}",
            "total_tokens": total_tokens,
            "consecutive_429_peak": self.consecutive_429,
            "cooldown_histogram": self.cooldown_histogram,
            "fallback_reasons": fallback_reasons,
        }
    
    def reset_counters(self):
        """Reset counters for new run."""
        self.consecutive_429 = 0
        self.last_429_time = 0.0
        self.recent_calls.clear()
        logger.info("[OptimizationPatchV2] Counters reset")


# Global instance
_patch_v2_instance: Optional[OptimizationPatchV2] = None


def get_optimization_patch_v2() -> OptimizationPatchV2:
    """Get or create the global optimization patch instance."""
    global _patch_v2_instance
    if _patch_v2_instance is None:
        _patch_v2_instance = OptimizationPatchV2()
    return _patch_v2_instance
