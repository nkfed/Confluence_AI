"""
Caching and batch processing for AI tag generation.

Features:
- Content hash-based caching for AI results
- Batch processing of multiple pages
- Cache invalidation based on page version
"""

import hashlib
from typing import Dict, List, Optional, Tuple
from src.core.logging.logger import get_logger

logger = get_logger(__name__)
cache_logger = get_logger("ai_cache")


class AIResultCache:
    """
    Cache for AI-generated tags based on page content hash.
    
    Invalidates cache when page version changes.
    """
    
    def __init__(self, max_size: int = 1000):
        self.cache: Dict[str, Dict] = {}
        self.max_size = max_size
        self.hits = 0
        self.misses = 0
    
    def _compute_hash(self, content: str) -> str:
        """Compute SHA256 hash of content."""
        return hashlib.sha256(content.encode()).hexdigest()
    
    def get(self, page_id: str, content: str, version: Optional[int] = None) -> Optional[Dict]:
        """
        Get cached AI result if available.
        
        Returns None if:
        - Cache miss
        - Version has changed
        """
        content_hash = self._compute_hash(content)
        cache_key = f"{page_id}:{content_hash}"
        
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            
            # Check if version matches
            if version is not None and cached.get("version") != version:
                cache_logger.debug(f"[CACHE] Version mismatch for {page_id}: invalidating")
                del self.cache[cache_key]
                self.misses += 1
                return None
            
            self.hits += 1
            cache_logger.debug(f"[CACHE] Hit for {page_id} ({content_hash[:8]})")
            return cached.get("result")
        
        self.misses += 1
        return None
    
    def set(self, page_id: str, content: str, result: Dict, version: Optional[int] = None):
        """Cache AI result."""
        if len(self.cache) >= self.max_size:
            # Simple eviction: remove oldest entry
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]
            cache_logger.debug(f"[CACHE] Evicted {oldest_key} (cache full)")
        
        content_hash = self._compute_hash(content)
        cache_key = f"{page_id}:{content_hash}"
        
        self.cache[cache_key] = {
            "result": result,
            "version": version,
            "content_hash": content_hash
        }
        
        cache_logger.debug(f"[CACHE] Cached result for {page_id} ({content_hash[:8]})")
    
    def get_stats(self) -> Dict:
        """Get cache statistics."""
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0
        return {
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": f"{hit_rate:.1f}%",
            "size": len(self.cache),
            "max_size": self.max_size
        }
    
    def clear(self):
        """Clear cache."""
        self.cache.clear()
        self.hits = 0
        self.misses = 0


class BatchProcessor:
    """
    Batch multiple pages for single AI call.
    
    Instead of N pages → N AI calls,
    group into batches: (N/batch_size) AI calls
    """
    
    def __init__(self, batch_size: int = 5):
        self.batch_size = int(batch_size)
        
        if self.batch_size < 1:
            self.batch_size = 1
        
        logger.info(f"[BatchProcessor] Initialized with batch_size={self.batch_size}")
    
    def create_batches(self, pages: List[Dict]) -> List[List[Dict]]:
        """
        Split pages into batches.
        
        Args:
            pages: List of page dicts with {page_id, content, ...}
        
        Returns:
            List of batches, each containing batch_size pages (or less for last batch)
        """
        batches = []
        for i in range(0, len(pages), self.batch_size):
            batch = pages[i:i + self.batch_size]
            batches.append(batch)
        
        logger.info(
            f"[BatchProcessor] Split {len(pages)} pages into {len(batches)} batches "
            f"(batch_size={self.batch_size})"
        )
        return batches
    
    @staticmethod
    def format_batch_for_ai(batch: List[Dict]) -> str:
        """
        Format a batch of pages into a structured prompt for AI.
        
        Example:
            Page 1 (ID: 123):
            Content: ...
            ---
            Page 2 (ID: 456):
            Content: ...
        """
        formatted = []
        for i, page in enumerate(batch, 1):
            page_id = page.get("page_id", "UNKNOWN")
            content = page.get("content", "")[:3000]  # Limit to 3000 chars per page
            
            formatted.append(f"Page {i} (ID: {page_id}):\n{content}")
        
        return "\n---\n".join(formatted)


# Global instances
_cache: Optional[AIResultCache] = None
_batch_processor: Optional[BatchProcessor] = None


def get_ai_cache() -> AIResultCache:
    """Get or create the global AI result cache."""
    global _cache
    if _cache is None:
        _cache = AIResultCache(max_size=1000)
    return _cache


def get_batch_processor() -> BatchProcessor:
    """Get or create the global batch processor."""
    global _batch_processor
    if _batch_processor is None:
        import os
        batch_size = int(os.getenv("TAG_SPACE_BATCH_SIZE", "5"))
        _batch_processor = BatchProcessor(batch_size=batch_size)
    return _batch_processor
