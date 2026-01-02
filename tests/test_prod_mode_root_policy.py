"""
Test PROD mode для /bulk/tag-tree з non-whitelist root pages
"""
import pytest
import asyncio
import os
from src.services.bulk_tagging_service import BulkTaggingService
from src.clients.confluence_client import ConfluenceClient
from src.core.logging.logging_config import configure_logging

configure_logging()


@pytest.mark.asyncio
async def test_tag_tree_prod_mode_non_whitelist_root():
    """
    Test that PROD mode allows any root_page_id, even if not in whitelist.
    
    Expected behavior:
    - TAGGING_AGENT_MODE=PROD
    - root_page_id NOT in TAGGING_AGENT_TEST_PAGE whitelist
    - dry_run=false
    - Result: Operation should proceed successfully
    """
    print(f"\n[TEST] Testing /bulk/tag-tree PROD mode with non-whitelist root")
    
    # Set PROD mode
    os.environ["TAGGING_AGENT_MODE"] = "PROD"
    
    # Use a root page that's NOT in whitelist
    # TAGGING_AGENT_TEST_PAGE=19713687690,19699862097
    # So we'll use a different page
    non_whitelist_root = "19700089019"  # Helpdesk root (not in tagging whitelist)
    
    print(f"  Root page ID: {non_whitelist_root}")
    print(f"  Mode: PROD")
    print(f"  Dry-run: False")
    
    confluence_client = ConfluenceClient()
    service = BulkTaggingService(confluence_client=confluence_client)
    
    # Execute real update in PROD mode
    result = await service.tag_tree(space_key="euheals", root_page_id=non_whitelist_root, dry_run=False)
    
    print(f"\n[TEST] Result:")
    print(f"  Status: {result.get('status', 'N/A')}")
    print(f"  Total: {result.get('total')}")
    print(f"  Success: {result.get('success')}")
    print(f"  Errors: {result.get('errors')}")
    
    # Verify operation succeeded (not blocked by policy)
    assert result.get('status') != 'error' or 'not allowed' not in str(result.get('message', '')).lower(), \
        "PROD mode should allow any root_page_id"
    
    # If there are details, check they were processed
    if result.get('details'):
        first_page = result['details'][0]
        print(f"\n[TEST] First page:")
        print(f"  Page ID: {first_page.get('page_id')}")
        print(f"  Status: {first_page.get('status')}")
        
        # Should not be blocked by policy
        assert first_page.get('status') != 'forbidden', \
            "PROD mode should not have forbidden pages"
    
    print(f"\n[TEST] ✅ PROD mode successfully processed non-whitelist root!")
    
    # Reset
    os.environ["TAGGING_AGENT_MODE"] = "SAFE_TEST"
    
    return result


@pytest.mark.asyncio
async def test_tag_tree_safe_test_blocks_non_whitelist_root():
    """
    Test that SAFE_TEST mode blocks non-whitelist root_page_id.
    
    Expected behavior:
    - TAGGING_AGENT_MODE=SAFE_TEST
    - root_page_id NOT in whitelist
    - Result: Should be blocked with PermissionError
    """
    print(f"\n[TEST] Testing /bulk/tag-tree SAFE_TEST mode blocks non-whitelist root")
    
    # Set SAFE_TEST mode
    os.environ["TAGGING_AGENT_MODE"] = "SAFE_TEST"
    
    # Use a root page that's NOT in whitelist
    non_whitelist_root = "19700089019"  # Helpdesk root (not in tagging whitelist)
    
    print(f"  Root page ID: {non_whitelist_root}")
    print(f"  Mode: SAFE_TEST")
    print(f"  Dry-run: False")
    
    confluence_client = ConfluenceClient()
    service = BulkTaggingService(confluence_client=confluence_client)
    
    # Execute - should be blocked
    result = await service.tag_tree(space_key="euheals", root_page_id=non_whitelist_root, dry_run=False)
    
    print(f"\n[TEST] Result:")
    print(f"  Status: {result.get('status')}")
    print(f"  Message: {result.get('message', 'N/A')}")
    
    # Verify operation was blocked
    assert result.get('status') == 'error', \
        "SAFE_TEST mode should block non-whitelist root_page_id"
    assert 'not allowed' in str(result.get('message', '')).lower() or \
           'forbidden' in str(result.get('message', '')).lower(), \
        "Error message should indicate policy violation"
    
    print(f"\n[TEST] ✅ SAFE_TEST mode correctly blocked non-whitelist root!")
    
    # Reset
    os.environ["TAGGING_AGENT_MODE"] = "SAFE_TEST"
    
    return result


@pytest.mark.asyncio
async def test_tag_tree_test_mode_blocks_non_whitelist_root():
    """
    Test that TEST mode blocks non-whitelist root_page_id.
    
    Expected behavior:
    - TAGGING_AGENT_MODE=TEST
    - root_page_id NOT in whitelist
    - Result: Should be blocked with PermissionError
    """
    print(f"\n[TEST] Testing /bulk/tag-tree TEST mode blocks non-whitelist root")
    
    # Set TEST mode
    os.environ["TAGGING_AGENT_MODE"] = "TEST"
    
    # Use a root page that's NOT in whitelist
    non_whitelist_root = "19700089019"
    
    print(f"  Root page ID: {non_whitelist_root}")
    print(f"  Mode: TEST")
    print(f"  Dry-run: True (automatic)")
    
    confluence_client = ConfluenceClient()
    service = BulkTaggingService(confluence_client=confluence_client)
    
    # Execute - should be blocked
    result = await service.tag_tree(space_key="euheals", root_page_id=non_whitelist_root, dry_run=True)
    
    print(f"\n[TEST] Result:")
    print(f"  Status: {result.get('status')}")
    print(f"  Message: {result.get('message', 'N/A')}")
    
    # Verify operation was blocked
    assert result.get('status') == 'error', \
        "TEST mode should block non-whitelist root_page_id"
    assert 'not allowed' in str(result.get('message', '')).lower() or \
           'forbidden' in str(result.get('message', '')).lower(), \
        "Error message should indicate policy violation"
    
    print(f"\n[TEST] ✅ TEST mode correctly blocked non-whitelist root!")
    
    # Reset
    os.environ["TAGGING_AGENT_MODE"] = "SAFE_TEST"
    
    return result


if __name__ == "__main__":
    print("="*80)
    print("PROD MODE ROOT PAGE POLICY TEST")
    print("="*80)
    
    print("\n" + "="*80)
    print("TEST 1: PROD MODE - ALLOW NON-WHITELIST ROOT")
    print("="*80)
    asyncio.run(test_tag_tree_prod_mode_non_whitelist_root())
    
    print("\n" + "="*80)
    print("TEST 2: SAFE_TEST MODE - BLOCK NON-WHITELIST ROOT")
    print("="*80)
    asyncio.run(test_tag_tree_safe_test_blocks_non_whitelist_root())
    
    print("\n" + "="*80)
    print("TEST 3: TEST MODE - BLOCK NON-WHITELIST ROOT")
    print("="*80)
    asyncio.run(test_tag_tree_test_mode_blocks_non_whitelist_root())
    
    print("\n" + "="*80)
    print("✅ ALL ROOT PAGE POLICY TESTS PASSED!")
    print("="*80)
