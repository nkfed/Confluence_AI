"""
Rate Limiting Module for AI Providers.

Provides simple local rate limiting to prevent API rate limit errors (429).
"""

import time
from dataclasses import dataclass
from typing import Optional
from src.core.logging.logger import get_logger

logger = get_logger(__name__)


@dataclass
class RateLimitConfig:
    """
    Rate limit configuration.
    
    Attributes:
        max_rpm: Maximum requests per minute
        min_interval_sec: Minimum interval between requests in seconds
    """
    max_rpm: int = 5  # max requests per minute
    min_interval_sec: float = 0.2  # minimal delay between calls (200ms)


class SimpleRateLimiter:
    """
    Simple local rate limiter for API calls.
    
    Features:
    - Guarantees minimum interval between requests
    - Enforces max requests per minute (RPM)
    - Blocks execution with time.sleep() when limits exceeded
    - Sliding window for RPM tracking
    
    Use this to prevent 429 rate limit errors from AI providers.
    
    Example:
        >>> config = RateLimitConfig(max_rpm=10, min_interval_sec=0.2)
        >>> limiter = SimpleRateLimiter(config)
        >>> 
        >>> # Before each API call
        >>> limiter.before_call()
        >>> response = await api_call()
    """
    
    def __init__(self, config: RateLimitConfig):
        """
        Initialize rate limiter with configuration.
        
        Args:
            config: Rate limit configuration
        """
        self.config = config
        self._last_call_ts: Optional[float] = None
        self._window_start_ts: float = time.time()
        self._requests_in_window: int = 0
        
        logger.debug(
            f"Rate limiter initialized: max_rpm={config.max_rpm}, "
            f"min_interval={config.min_interval_sec}s"
        )
    
    def before_call(self) -> None:
        """
        Call this before making an API request.
        
        This method will:
        1. Enforce minimum interval between requests
        2. Track requests in current minute window
        3. Block if RPM limit exceeded until next window
        
        Blocks execution using time.sleep() if necessary.
        """
        now = time.time()
        
        # 1. Enforce minimum interval between requests
        if self._last_call_ts is not None:
            elapsed = now - self._last_call_ts
            if elapsed < self.config.min_interval_sec:
                sleep_time = self.config.min_interval_sec - elapsed
                logger.debug(f"Rate limit: sleeping {sleep_time:.3f}s (min interval)")
                time.sleep(sleep_time)
                now = time.time()
        
        # 2. Update minute window
        window_age = now - self._window_start_ts
        if window_age >= 60.0:
            logger.debug(
                f"Rate limit: new window (prev window: {self._requests_in_window} requests)"
            )
            self._window_start_ts = now
            self._requests_in_window = 0
        
        # 3. Check RPM limit
        if self._requests_in_window >= self.config.max_rpm:
            sleep_for = 60.0 - (now - self._window_start_ts)
            if sleep_for > 0:
                logger.warning(
                    f"Rate limit: RPM limit reached ({self.config.max_rpm}), "
                    f"sleeping {sleep_for:.1f}s"
                )
                time.sleep(sleep_for)
            
            # Reset window
            self._window_start_ts = time.time()
            self._requests_in_window = 0
        
        # Track this request
        self._requests_in_window += 1
        self._last_call_ts = time.time()
        
        logger.debug(
            f"Rate limit check passed: request {self._requests_in_window}/{self.config.max_rpm}"
        )
    
    def get_stats(self) -> dict:
        """
        Get current rate limiter statistics.
        
        Returns:
            dict: Statistics including requests in window, window age, etc.
        """
        now = time.time()
        window_age = now - self._window_start_ts
        
        return {
            "requests_in_window": self._requests_in_window,
            "max_rpm": self.config.max_rpm,
            "window_age_sec": window_age,
            "window_remaining_sec": max(0, 60.0 - window_age),
            "can_make_request": self._requests_in_window < self.config.max_rpm,
            "last_call_ago_sec": (now - self._last_call_ts) if self._last_call_ts else None,
        }


__all__ = ["RateLimitConfig", "SimpleRateLimiter"]
