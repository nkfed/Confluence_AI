"""
Test script for tag-space with optimization patch validation.
"""
import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.services.bulk_tagging_service import BulkTaggingService
from src.clients.confluence_client import ConfluenceClient
from src.agents.tagging_agent import TaggingAgent
from src.core.logging.logger import get_logger

logger = get_logger(__name__)


async def main():
    """Run tag-space test on euheals space."""
    
    print("=" * 80)
    print("TAG-SPACE OPTIMIZATION PATCH VALIDATION TEST")
    print("=" * 80)
    print(f"Space: euheals")
    print(f"Mode: DEBUG + DRY-RUN")
    print(f"Expected: 90%+ Gemini success, <8% fallback")
    print("=" * 80)
    print()
    
    # Initialize components
    logger.info("Initializing Confluence client...")
    confluence = ConfluenceClient()
    
    logger.info("Initializing Tagging agent...")
    tagging_agent = TaggingAgent()
    
    logger.info("Initializing BulkTaggingService...")
    service = BulkTaggingService(confluence, tagging_agent)
    
    # Run tag-space
    space_key = "euheals"
    
    try:
        logger.info(f"Starting tag-space operation on '{space_key}'...")
        print(f"\n🚀 Starting tag-space operation on '{space_key}'...\n")
        
        result = await service.tag_space(
            space_key=space_key,
            dry_run=True  # Safe mode - no actual updates
        )
        
        # Display results
        print("\n" + "=" * 80)
        print("RESULTS")
        print("=" * 80)
        
        if "error" in result:
            print(f"❌ Error: {result['error']}")
            return
        
        # Extract metrics
        processed = result.get("processed", 0)
        total = result.get("total", 0)
        errors = result.get("errors", 0)
        
        print(f"✅ Processed: {processed}/{total} pages")
        print(f"⚠️  Errors: {errors}")
        
        # Cache stats
        if "cache_stats" in result:
            cache = result["cache_stats"]
            print(f"\n📦 Cache Stats:")
            print(f"   Hits: {cache.get('hits', 0)}")
            print(f"   Misses: {cache.get('misses', 0)}")
            print(f"   Hit Rate: {cache.get('hit_rate', '0%')}")
        
        # Concurrency metrics
        if "concurrency_metrics" in result:
            metrics = result["concurrency_metrics"]
            print(f"\n⚙️  Concurrency Metrics:")
            print(f"   Total AI calls: {metrics.get('total_ai_calls', 0)}")
            print(f"   Successful: {metrics.get('successful_calls', 0)}")
            print(f"   Failed: {metrics.get('failed_calls', 0)}")
            print(f"   Rate limits (429): {metrics.get('rate_limit_errors', 0)}")
            print(f"   Fallbacks to OpenAI: {metrics.get('fallback_switches', 0)}")
            print(f"   Current concurrency: {metrics.get('current_concurrency', 'N/A')}")
            
            # Calculate success rate
            total_calls = metrics.get('total_ai_calls', 0)
            successful = metrics.get('successful_calls', 0)
            rate_limits = metrics.get('rate_limit_errors', 0)
            fallbacks = metrics.get('fallback_switches', 0)
            
            if total_calls > 0:
                gemini_success_rate = ((successful - fallbacks) / total_calls) * 100
                fallback_rate = (fallbacks / total_calls) * 100
                
                print(f"\n📊 PATCH VALIDATION:")
                print(f"   Gemini Success Rate: {gemini_success_rate:.1f}% (target: 90%+)")
                print(f"   Fallback Rate: {fallback_rate:.1f}% (target: <8%)")
                print(f"   429 Errors: {rate_limits}")
                
                # Validation
                validation_passed = gemini_success_rate >= 90 and fallback_rate < 8
                if validation_passed:
                    print(f"\n✅ PATCH VALIDATION: PASSED")
                else:
                    print(f"\n⚠️  PATCH VALIDATION: NEEDS TUNING")
                    if gemini_success_rate < 90:
                        print(f"      - Gemini success rate below target")
                    if fallback_rate >= 8:
                        print(f"      - Fallback rate above target")
        
        print("\n" + "=" * 80)
        
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        print(f"\n❌ Test failed: {e}")
        return
    
    finally:
        # ConfluenceClient doesn't need async close
        print("\n✅ Test completed. Check logs for detailed information.")


if __name__ == "__main__":
    asyncio.run(main())
