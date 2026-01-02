"""
Test bulk tag-space endpoint with proper error handling
"""
import pytest
import asyncio
from src.services.bulk_tagging_service import BulkTaggingService
from src.core.logging.logging_config import configure_logging
import os

configure_logging()


@pytest.mark.asyncio
async def test_tag_space_dry_run():
    """
    Test tag-space in dry-run mode (TEST mode).
    
    Should fetch all pages from space and tag them without updates.
    """
    # Override to TEST mode
    os.environ["TAGGING_AGENT_MODE"] = "TEST"
    
    service = BulkTaggingService()
    
    # Use a known space key (your personal workspace or test space)
    space_key = "~712020f8b521f61d59302b99b92bc85f0df23b"  # Example
    
    print(f"\n[TEST] Tagging space '{space_key}' in TEST mode (dry-run)")
    
    result = await service.tag_space(space_key, dry_run=None)  # None = use agent mode
    
    print(f"\n[TEST] Result:")
    print(f"  Total: {result.get('total')}")
    print(f"  Processed: {result.get('processed')}")
    print(f"  Success: {result.get('success')}")
    print(f"  Errors: {result.get('errors')}")
    print(f"  Dry-run: {result.get('dry_run')}")
    
    # Verify structure
    assert "total" in result
    assert "processed" in result
    assert "success" in result
    assert "errors" in result
    assert "dry_run" in result
    assert "details" in result
    
    # In TEST mode, dry_run should be True
    assert result["dry_run"] == True, "TEST mode should be dry-run"
    
    # Check some pages were found
    if result["total"] > 0:
        print(f"\n[TEST] Found {result['total']} pages in space")
        print(f"[TEST] First 3 pages:")
        for detail in result["details"][:3]:
            print(f"  - Page {detail.get('page_id')}: {detail.get('status')}")
    else:
        print(f"\n[TEST] No pages found in space (might be empty or invalid)")
    
    print(f"\n[TEST] ✅ Dry-run test passed!")
    
    # Reset environment
    os.environ["TAGGING_AGENT_MODE"] = "TEST"


@pytest.mark.asyncio
async def test_tag_space_invalid_space():
    """
    Test tag-space with invalid space key.
    
    Should return proper error response without crashing.
    """
    os.environ["TAGGING_AGENT_MODE"] = "TEST"
    
    service = BulkTaggingService()
    
    # Use invalid space key
    space_key = "INVALID_SPACE_12345"
    
    print(f"\n[TEST] Tagging invalid space '{space_key}'")
    
    result = await service.tag_space(space_key, dry_run=True)

    # Updated checks for new response structure
    assert "task_id" in result
    assert isinstance(result["task_id"], str)
    assert "status" in result or "details" in result
    
    print(f"\n[TEST] Result:")
    print(f"  Task ID: {result.get('task_id')}")
    print(f"  Status: {result.get('status')}")
    
    # Verify error handling
    assert "details" in result
    if result["details"]:
        detail = result["details"][0]
        assert detail.get("status") == "error"
        assert "message" in detail
        print(f"  Message: {detail.get('message')}")
    
    print(f"\n[TEST] ✅ Invalid space test passed!")
    
    # Reset environment
    os.environ["TAGGING_AGENT_MODE"] = "TEST"


@pytest.mark.asyncio
async def test_tag_space_prod_mode():
    """
    Test tag-space in PROD mode with explicit dry_run=True.
    
    Should use explicit dry_run parameter instead of agent mode.
    """
    # Override to PROD mode
    os.environ["TAGGING_AGENT_MODE"] = "PROD"
    
    service = BulkTaggingService()
    
    # Use a known space key
    space_key = "~712020f8b521f61d59302b99b92bc85f0df23b"
    
    print(f"\n[TEST] Tagging space '{space_key}' in PROD mode with explicit dry_run=True")
    
    # Even in PROD, explicit dry_run=True should work
    result = await service.tag_space(space_key, dry_run=True)
    
    print(f"\n[TEST] Result:")
    print(f"  Total: {result.get('total')}")
    print(f"  Dry-run: {result.get('dry_run')}")
    
    # Verify explicit dry_run is respected
    assert result["dry_run"] == True, "Explicit dry_run=True should be respected"
    
    print(f"\n[TEST] ✅ PROD mode with explicit dry_run test passed!")
    
    # Reset environment
    os.environ["TAGGING_AGENT_MODE"] = "TEST"


@pytest.mark.asyncio
async def test_tag_space_response_structure():
    """
    Test that tag-space response has proper structure per page.
    
    Each page should have:
    - page_id
    - status
    - tags (structured or null)
    """
    os.environ["TAGGING_AGENT_MODE"] = "TEST"
    
    service = BulkTaggingService()
    space_key = "~712020f8b521f61d59302b99b92bc85f0df23b"
    
    print(f"\n[TEST] Checking response structure for space '{space_key}'")
    
    result = await service.tag_space(space_key, dry_run=True)
    
    # Check top-level structure
    assert "total" in result
    assert "processed" in result
    assert "success" in result
    assert "errors" in result
    assert "dry_run" in result
    assert "details" in result
    
    # Check per-page structure
    if result["total"] > 0:
        for detail in result["details"]:
            assert "page_id" in detail or "space_key" in detail, "Each detail should have page_id or space_key"
            assert "status" in detail, "Each detail should have status"
            
            if detail.get("status") == "error":
                assert detail.get("tags") is None, "Error status should have tags=null"
                assert "message" in detail, "Error status should have message"
            else:
                assert "tags" in detail, "Non-error status should have tags field"
                
                if detail.get("tags") is not None:
                    tags = detail["tags"]
                    assert "proposed" in tags
                    assert "existing" in tags
                    
                    if detail.get("status") == "dry_run":
                        assert "to_add" in tags
                    elif detail.get("status") == "updated":
                        assert "added" in tags
        
        print(f"\n[TEST] ✅ Response structure is correct for {len(result['details'])} pages!")
    else:
        print(f"\n[TEST] ⚠️ No pages found in space, skipping structure check")
    
    # Reset environment
    os.environ["TAGGING_AGENT_MODE"] = "TEST"


if __name__ == "__main__":
    print("="*80)
    print("BULK TAG-SPACE ERROR HANDLING TEST")
    print("="*80)
    
    print("\n" + "="*80)
    print("TEST 1: DRY-RUN MODE")
    print("="*80)
    asyncio.run(test_tag_space_dry_run())
    
    print("\n" + "="*80)
    print("TEST 2: INVALID SPACE")
    print("="*80)
    asyncio.run(test_tag_space_invalid_space())
    
    print("\n" + "="*80)
    print("TEST 3: PROD MODE WITH EXPLICIT DRY_RUN")
    print("="*80)
    asyncio.run(test_tag_space_prod_mode())
    
    print("\n" + "="*80)
    print("TEST 4: RESPONSE STRUCTURE")
    print("="*80)
    asyncio.run(test_tag_space_response_structure())
    
    print("="*80)
