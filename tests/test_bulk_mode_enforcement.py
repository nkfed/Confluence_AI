"""
Test PROD mode in bulk tagging - all pages should be allowed
"""
import pytest
import asyncio
from src.services.bulk_tagging_service import BulkTaggingService
from src.core.logging.logging_config import configure_logging
import os

configure_logging()


@pytest.mark.asyncio
async def test_bulk_tagging_prod_mode():
    """
    Test that PROD mode allows ALL pages (no whitelist filtering).
    
    - Set TAGGING_AGENT_MODE=PROD
    - Submit pages not in whitelist
    - Verify they are processed (not skipped)
    """
    # Override mode to PROD
    os.environ["TAGGING_AGENT_MODE"] = "PROD"
    
    service = BulkTaggingService()
    
    # Verify agent is in PROD mode
    assert service.agent.mode == "PROD", f"Expected PROD mode, got {service.agent.mode}"
    
    print(f"\n[TEST] Agent mode: {service.agent.mode}")
    print(f"[TEST] Agent whitelist: {service.agent.allowed_test_pages}")
    
    # Use 2 test pages - one in whitelist, one not
    whitelist_page = "19713687690"  # In TAGGING_AGENT_TEST_PAGE
    non_whitelist_page = "19700089019"  # Not in TAGGING_AGENT_TEST_PAGE (but in ALLOWED_TAGGING_PAGES)
    
    page_ids = [whitelist_page, non_whitelist_page]
    
    print(f"\n[TEST] Testing bulk tagging in PROD mode with {len(page_ids)} pages")
    print(f"  Whitelist page: {whitelist_page}")
    print(f"  Non-whitelist page: {non_whitelist_page}")
    
    # Run with dry_run=False (real update)
    result = await service.tag_pages(page_ids, space_key="euheals", dry_run=False)
    
    print(f"\n[TEST] Result:")
    print(f"  Total: {result.get('total')}")
    print(f"  Processed: {result.get('processed')}")
    print(f"  Success: {result.get('success')}")
    print(f"  Errors: {result.get('errors')}")
    print(f"  Dry-run: {result.get('dry_run')}")
    
    # Verify ALL pages were processed (not skipped due to whitelist)
    assert result["total"] == 2, "Expected 2 pages total"
    assert result["processed"] == 2, "Expected 2 pages processed"
    assert "skipped_due_to_whitelist" not in result, "Should not have skipped_due_to_whitelist in PROD"
    
    # Check details
    statuses = [d["status"] for d in result["details"]]
    print(f"\n[TEST] Statuses: {statuses}")
    
    # In PROD mode, both pages should be updated (not forbidden/skipped)
    for detail in result["details"]:
        assert detail["status"] in ["updated", "error"], \
            f"Expected 'updated' or 'error', got {detail['status']} for page {detail['page_id']}"
        
        if detail["status"] == "updated":
            print(f"  Page {detail['page_id']}: ✅ updated")
    
    print(f"\n[TEST] ✅ PROD mode test passed - all pages processed!")
    
    # Reset environment
    os.environ["TAGGING_AGENT_MODE"] = "TEST"


@pytest.mark.asyncio
async def test_bulk_tagging_safe_test_mode():
    """
    Test that SAFE_TEST mode blocks non-whitelist pages.
    
    - Set TAGGING_AGENT_MODE=SAFE_TEST
    - Submit pages not in TAGGING_AGENT_TEST_PAGE
    - Verify they are forbidden
    """
    # Override mode to SAFE_TEST
    os.environ["TAGGING_AGENT_MODE"] = "SAFE_TEST"
    
    service = BulkTaggingService()
    
    # Verify agent is in SAFE_TEST mode
    assert service.agent.mode == "SAFE_TEST", f"Expected SAFE_TEST mode, got {service.agent.mode}"
    
    print(f"\n[TEST] Agent mode: {service.agent.mode}")
    print(f"[TEST] Agent whitelist: {service.agent.allowed_test_pages}")
    
    # Use 2 pages - one in whitelist, one not
    whitelist_page = "19713687690"  # In TAGGING_AGENT_TEST_PAGE
    non_whitelist_page = "19700089019"  # Not in TAGGING_AGENT_TEST_PAGE
    
    page_ids = [whitelist_page, non_whitelist_page]
    
    print(f"\n[TEST] Testing bulk tagging in SAFE_TEST mode")
    
    # Run with dry_run=False
    result = await service.tag_pages(page_ids, space_key="euheals", dry_run=False)
    
    print(f"\n[TEST] Result:")
    print(f"  Total: {result.get('total')}")
    print(f"  Processed: {result.get('processed')}")
    print(f"  Success: {result.get('success')}")
    
    # Check details
    for detail in result["details"]:
        page_id = detail["page_id"]
        status = detail["status"]
        
        print(f"  Page {page_id}: {status}")
        
        if page_id == whitelist_page:
            assert status == "updated", f"Whitelist page should be updated in SAFE_TEST"
        elif page_id == non_whitelist_page:
            assert status == "forbidden", f"Non-whitelist page should be forbidden in SAFE_TEST"
    
    print(f"\n[TEST] ✅ SAFE_TEST mode test passed!")
    
    # Reset environment
    os.environ["TAGGING_AGENT_MODE"] = "TEST"


@pytest.mark.asyncio
async def test_bulk_tagging_test_mode():
    """
    Test that TEST mode blocks ALL updates (dry-run only).
    
    - Set TAGGING_AGENT_MODE=TEST
    - Submit any pages with dry_run=False
    - Verify all are forbidden
    """
    # Override mode to TEST
    os.environ["TAGGING_AGENT_MODE"] = "TEST"
    
    service = BulkTaggingService()
    
    # Verify agent is in TEST mode
    assert service.agent.mode == "TEST", f"Expected TEST mode, got {service.agent.mode}"
    
    print(f"\n[TEST] Agent mode: {service.agent.mode}")
    
    # Use 1 whitelist page
    page_ids = ["19713687690"]
    
    print(f"\n[TEST] Testing bulk tagging in TEST mode with dry_run=False")
    
    # Run with dry_run=False (should still be blocked)
    result = await service.tag_pages(page_ids, space_key="euheals", dry_run=False)
    
    print(f"\n[TEST] Result:")
    for detail in result["details"]:
        print(f"  Page {detail['page_id']}: {detail['status']}")
        
        # In TEST mode, even dry_run=False should be blocked
        assert detail["status"] == "forbidden", \
            f"TEST mode should block all updates, got {detail['status']}"
    
    print(f"\n[TEST] ✅ TEST mode test passed - all updates blocked!")


if __name__ == "__main__":
    print("="*80)
    print("BULK TAGGING MODE ENFORCEMENT TEST")
    print("="*80)
    
    print("\n" + "="*80)
    print("TEST 1: PROD MODE - ALL PAGES ALLOWED")
    print("="*80)
    asyncio.run(test_bulk_tagging_prod_mode())
    
    print("\n" + "="*80)
    print("TEST 2: SAFE_TEST MODE - WHITELIST ONLY")
    print("="*80)
    asyncio.run(test_bulk_tagging_safe_test_mode())
    
    print("\n" + "="*80)
    print("TEST 3: TEST MODE - ALL UPDATES BLOCKED")
    print("="*80)
    asyncio.run(test_bulk_tagging_test_mode())
    
    print("="*80)
