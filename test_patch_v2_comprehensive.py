"""
Comprehensive test for Optimization Patch v2.0
- 20 AI operations on euheals space
- Various payload types
- Micro-batching support
- Detailed metrics collection
"""

import asyncio
import sys
import os
import time
from typing import List, Dict, Any

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.services.bulk_tagging_service import BulkTaggingService
from src.clients.confluence_client import ConfluenceClient
from src.agents.tagging_agent import TaggingAgent
from src.core.logging.logger import get_logger
from src.core.ai.optimization_patch_v2 import get_optimization_patch_v2

logger = get_logger(__name__)


async def main():
    """Run comprehensive test with 20 operations."""
    
    print("=" * 90)
    print("OPTIMIZATION PATCH v2.0 — COMPREHENSIVE TEST")
    print("=" * 90)
    print(f"Space: euheals")
    print(f"Operations: 20")
    print(f"Mode: DRY-RUN with metrics collection")
    print("=" * 90)
    print()
    
    # Initialize components
    logger.info("Initializing components...")
    confluence = ConfluenceClient()
    tagging_agent = TaggingAgent()
    service = BulkTaggingService(confluence, tagging_agent)
    patch = get_optimization_patch_v2()
    
    # Reset patch state
    patch.reset_counters()
    
    # Get pages from euheals space
    space_key = "euheals"
    
    try:
        print(f"\n[1/3] Fetching pages from '{space_key}'...\n")
        
        # Get all pages from space (or up to 20)
        pages_data = []
        
        # Use confluence client to get space pages
        logger.info(f"Fetching pages from space '{space_key}'")
        
        # Get the space to fetch pages
        import requests
        
        base_url = confluence.base_url
        space_url = f"{base_url}/wiki/rest/api/space/{space_key}"
        
        # Get all pages in space
        pages_url = f"{base_url}/wiki/rest/api/content?spaceKey={space_key}&limit=50&type=page"
        
        try:
            response = requests.get(pages_url, auth=confluence.auth, headers=confluence.headers, timeout=30)
            response.raise_for_status()
            pages_response = response.json()
            
            page_ids = [page["id"] for page in pages_response.get("results", [])][:20]
            
            if not page_ids:
                print("ERROR: No pages found in space")
                return
            
            print(f"Found {len(page_ids)} pages to process\n")
            
        except Exception as e:
            logger.error(f"Error fetching pages: {e}")
            print(f"ERROR: Failed to fetch pages: {e}")
            return
        
        # Process pages with metrics
        print(f"[2/3] Processing {len(page_ids)} pages with Optimization Patch v2...\n")
        
        start_time = time.time()
        
        # Use tag_pages to process all pages
        result = await service.tag_pages(
            page_ids=page_ids,
            space_key=space_key,
            dry_run=True,
            task_id="test_patch_v2"
        )
        
        elapsed = time.time() - start_time
        
        # Get statistics from patch
        print(f"\n[3/3] Collecting statistics...\n")
        
        stats = patch.get_statistics()
        
        # Display results
        print("\n" + "=" * 90)
        print("TEST RESULTS")
        print("=" * 90)
        
        print(f"\nPages Processed:")
        print(f"  Total: {result.get('processed', 0)}/{len(page_ids)}")
        print(f"  Errors: {result.get('errors', 0)}")
        print(f"  Duration: {elapsed:.1f}s")
        
        print(f"\nAI Call Metrics:")
        print(f"  Total calls: {stats['total_calls']}")
        print(f"  Gemini calls: {stats['gemini_calls']}")
        print(f"  Gemini success: {stats['gemini_success']}")
        print(f"  Gemini success rate: {stats['gemini_success_rate']}")
        print(f"  Fallback calls: {stats['fallback_calls']}")
        print(f"  Fallback rate: {stats['fallback_rate']}")
        
        print(f"\nPerformance Metrics:")
        print(f"  Avg duration: {stats['avg_duration_ms']}ms")
        print(f"  Total tokens: {stats['total_tokens']}")
        
        print(f"\nAdaptive Cooldown:")
        print(f"  Consecutive 429 peak: {stats['consecutive_429_peak']}")
        print(f"  Cooldown histogram:")
        for reason, count in stats['cooldown_histogram'].items():
            if count > 0:
                print(f"    - {reason}: {count}")
        
        if stats['fallback_reasons']:
            print(f"\nFallback Reasons:")
            for reason, count in stats['fallback_reasons'].items():
                print(f"  - {reason}: {count}")
        
        print(f"\nCache Stats:")
        cache_stats = result.get("cache_stats", {})
        if cache_stats:
            print(f"  Cache hits: {cache_stats.get('hits', 0)}")
            print(f"  Cache misses: {cache_stats.get('misses', 0)}")
            print(f"  Hit rate: {cache_stats.get('hit_rate', 'N/A')}")
        
        print("\n" + "=" * 90)
        
        # Validation
        gemini_success_rate = float(stats['gemini_success_rate'].rstrip('%'))
        fallback_rate = float(stats['fallback_rate'].rstrip('%'))
        
        print(f"\nPATCH VALIDATION:")
        print(f"  Target Gemini rate: >90%")
        print(f"  Actual: {stats['gemini_success_rate']}")
        
        if gemini_success_rate >= 90 and fallback_rate <= 10:
            print(f"  Status: PASSED ✅")
        elif gemini_success_rate >= 75 and fallback_rate <= 25:
            print(f"  Status: ACCEPTABLE (needs fine-tuning) ⚠️")
        else:
            print(f"  Status: NEEDS IMPROVEMENT ❌")
        
        print("\n" + "=" * 90)
        
        return {
            "pages_processed": result.get('processed', 0),
            "pages_total": len(page_ids),
            "elapsed_seconds": elapsed,
            "stats": stats
        }
        
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        print(f"\nERROR: Test failed: {e}")
        return None
    
    finally:
        print("\nTest completed. Check logs for detailed information.")


if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)
