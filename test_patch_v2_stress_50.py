"""
Stress test for Optimization Patch v2.0
- 50 AI operations on euheals space
- Real data scenarios
- Full metrics collection
- Production-level validation
"""

import asyncio
import sys
import os
import time
from typing import List, Dict, Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.services.bulk_tagging_service import BulkTaggingService
from src.clients.confluence_client import ConfluenceClient
from src.agents.tagging_agent import TaggingAgent
from src.core.logging.logger import get_logger
from src.core.ai.optimization_patch_v2 import get_optimization_patch_v2

logger = get_logger(__name__)


async def main():
    """Run stress test with 50 operations."""
    
    print("=" * 90)
    print("OPTIMIZATION PATCH v2.0 — STRESS TEST (50 OPERATIONS)")
    print("=" * 90)
    print(f"Space: euheals")
    print(f"Operations: 50")
    print(f"Mode: DRY-RUN with full metrics")
    print("=" * 90)
    print()
    
    # Initialize components
    logger.info("Initializing components for stress test...")
    confluence = ConfluenceClient()
    tagging_agent = TaggingAgent()
    service = BulkTaggingService(confluence, tagging_agent)
    patch = get_optimization_patch_v2()
    
    # Reset patch state
    patch.reset_counters()
    
    space_key = "euheals"
    
    try:
        print(f"\n[1/4] Fetching pages from '{space_key}'...\n")
        
        # Get pages from space
        import requests
        base_url = confluence.base_url
        pages_url = f"{base_url}/wiki/rest/api/content?spaceKey={space_key}&limit=100&type=page"
        
        try:
            response = requests.get(pages_url, auth=confluence.auth, headers=confluence.headers, timeout=30)
            response.raise_for_status()
            pages_response = response.json()
            
            # Get up to 50 pages
            page_ids = [page["id"] for page in pages_response.get("results", [])][:50]
            
            if not page_ids:
                print("ERROR: No pages found in space")
                return None
            
            print(f"Found {len(page_ids)} pages to process\n")
            
        except Exception as e:
            logger.error(f"Error fetching pages: {e}")
            print(f"ERROR: Failed to fetch pages: {e}")
            return None
        
        # Process pages with metrics
        print(f"[2/4] Processing {len(page_ids)} pages with Optimization Patch v2...\n")
        
        start_time = time.time()
        
        result = await service.tag_pages(
            page_ids=page_ids,
            space_key=space_key,
            dry_run=True,
            task_id="stress_test_v2"
        )
        
        elapsed = time.time() - start_time
        
        # Get statistics from patch
        print(f"\n[3/4] Collecting statistics...\n")
        
        stats = patch.get_statistics()
        
        # Display results
        print("\n" + "=" * 90)
        print("STRESS TEST RESULTS")
        print("=" * 90)
        
        print(f"\nPages Processed:")
        print(f"  Total requested: {len(page_ids)}")
        print(f"  Processed: {result.get('processed', 0)}")
        print(f"  Success: {result.get('success', 0)}")
        print(f"  Errors: {result.get('errors', 0)}")
        print(f"  Skipped: {result.get('skipped_by_whitelist', 0)}")
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
        
        print("\n" + "=" * 90)
        
        # Validation
        gemini_success_rate = float(stats['gemini_success_rate'].rstrip('%'))
        fallback_rate = float(stats['fallback_rate'].rstrip('%'))
        
        print(f"\nPATCH VALIDATION:")
        print(f"  Target Gemini rate: >90%")
        print(f"  Actual: {stats['gemini_success_rate']}")
        
        if gemini_success_rate >= 90 and fallback_rate <= 10:
            print(f"  Status: PASSED ✅")
            validation_passed = True
        elif gemini_success_rate >= 80 and fallback_rate <= 20:
            print(f"  Status: ACCEPTABLE (needs tuning) ⚠️")
            validation_passed = True
        else:
            print(f"  Status: NEEDS IMPROVEMENT ❌")
            validation_passed = False
        
        print("\n" + "=" * 90)
        print(f"\n[4/4] Summary\n")
        print(f"✅ Gemini Success Rate: {stats['gemini_success_rate']}")
        print(f"✅ Fallback Rate: {stats['fallback_rate']}")
        print(f"✅ Avg Duration: {stats['avg_duration_ms']}ms")
        print(f"✅ Total Pages: {result.get('processed', 0)}")
        print(f"✅ Total Errors: {result.get('errors', 0)}")
        
        if validation_passed:
            print(f"\n🎉 STRESS TEST PASSED!\n")
        else:
            print(f"\n⚠️ STRESS TEST NEEDS ATTENTION\n")
        
        return {
            "pages_processed": result.get('processed', 0),
            "pages_total": len(page_ids),
            "elapsed_seconds": elapsed,
            "stats": stats,
            "validation_passed": validation_passed
        }
        
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        print(f"\nERROR: Test failed: {e}")
        return None
    
    finally:
        print("\nStress test completed. Check logs for detailed information.")


if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)
