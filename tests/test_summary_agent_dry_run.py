"""
Test SummaryAgent dry-run behavior for whitelisted pages in TEST mode
"""
import pytest
import asyncio
import os

# Setup test environment
os.environ["SUMMARY_AGENT_MODE"] = "TEST"
os.environ["SUMMARY_AGENT_TEST_PAGE"] = "19699862097"

from src.agents.summary_agent import SummaryAgent
from src.core.logging.logging_config import configure_logging

configure_logging()


@pytest.mark.asyncio
async def test_summary_agent_dry_run_for_whitelisted_page():
    """
    Test that SummaryAgent in TEST mode:
    1. Allows whitelisted pages (no PermissionError)
    2. Generates summary via OpenAI
    3. Does NOT write to Confluence
    4. Returns dry_run status
    """
    # 1. Initialize agent
    agent = SummaryAgent()
    
    # 2. Verify agent configuration
    assert agent.mode == "TEST", f"Expected mode=TEST, got {agent.mode}"
    assert agent.is_dry_run() is True, "Expected is_dry_run()=True"
    assert "19699862097" in agent.allowed_test_pages, "Page should be in whitelist"
    
    print(f"\n[TEST] Agent configuration:")
    print(f"  Mode: {agent.mode}")
    print(f"  Dry-run: {agent.is_dry_run()}")
    print(f"  Whitelist: {agent.allowed_test_pages}")
    
    # 3. Get initial page state
    page_id = "19699862097"
    initial_page = await agent.confluence.get_page(page_id)
    initial_version = initial_page["version"]["number"]
    initial_length = len(initial_page["body"]["storage"]["value"])
    
    print(f"\n[TEST] Initial page state:")
    print(f"  Version: {initial_version}")
    print(f"  Content length: {initial_length} chars")
    
    # 4. Call update_page_with_summary (should perform dry-run)
    print(f"\n[TEST] Calling update_page_with_summary({page_id})...")
    result = await agent.update_page_with_summary(page_id)
    
    # 5. Verify dry-run result
    print(f"\n[TEST] Result:")
    print(f"  Status: {result.get('status')}")
    print(f"  Summary added: {result.get('summary_added')}")
    print(f"  Message: {result.get('message')}")
    
    assert result["status"] == "dry_run", f"Expected status=dry_run, got {result.get('status')}"
    assert result["summary_added"] is False, "Expected summary_added=False"
    assert "NOT written to Confluence" in result["message"], "Expected dry-run message"
    assert "page_id" in result, "Expected page_id in result"
    assert "title" in result, "Expected title in result"
    assert "summary_tokens_estimate" in result, "Expected token estimate"
    
    # 6. Verify page was NOT modified
    final_page = await agent.confluence.get_page(page_id)
    final_version = final_page["version"]["number"]
    final_length = len(final_page["body"]["storage"]["value"])
    
    print(f"\n[TEST] Final page state:")
    print(f"  Version: {final_version}")
    print(f"  Content length: {final_length} chars")
    
    assert initial_version == final_version, \
        f"Page version changed ({initial_version} → {final_version}), but shouldn't in dry-run"
    assert initial_length == final_length, \
        f"Content length changed ({initial_length} → {final_length}), but shouldn't in dry-run"
    
    # 7. Verify no PermissionError was raised
    print(f"\n[TEST] ✅ No PermissionError raised for whitelisted page")
    
    # 8. Verify summary was generated
    assert result.get("summary_tokens_estimate") > 0, "Summary should have been generated"
    print(f"[TEST] ✅ Summary generated ({result.get('summary_tokens_estimate')} tokens)")
    
    print(f"\n[TEST] ✅ All assertions passed!")
    print(f"[TEST] ✅ Dry-run behavior confirmed:")
    print(f"  - Whitelisted page allowed")
    print(f"  - Summary generated via OpenAI")
    print(f"  - Page NOT modified in Confluence")
    print(f"  - Dry-run status returned")


@pytest.mark.asyncio
async def test_summary_agent_blocks_non_whitelisted_page_in_test_mode():
    """
    Test that SummaryAgent in TEST mode blocks non-whitelisted pages
    """
    agent = SummaryAgent()
    
    # Try to process page NOT in whitelist
    non_whitelisted_page = "19700089019"
    assert non_whitelisted_page not in agent.allowed_test_pages
    
    print(f"\n[TEST] Attempting to process non-whitelisted page {non_whitelisted_page}...")
    
    # Should raise PermissionError
    with pytest.raises(PermissionError) as exc_info:
        await agent.update_page_with_summary(non_whitelisted_page)
    
    error_message = str(exc_info.value)
    assert "forbidden in TEST mode" in error_message
    assert non_whitelisted_page in error_message
    
    print(f"[TEST] ✅ PermissionError raised as expected:")
    print(f"  {error_message[:100]}...")


@pytest.mark.asyncio
async def test_summary_agent_safe_test_allows_update():
    """
    Test that SummaryAgent in SAFE_TEST mode:
    1. Allows whitelisted pages
    2. Generates summary via OpenAI
    3. DOES write to Confluence (real update)
    4. Returns updated status
    """
    # Override environment for this test
    import os
    original_mode = os.environ.get("SUMMARY_AGENT_MODE")
    os.environ["SUMMARY_AGENT_MODE"] = "SAFE_TEST"
    
    try:
        # 1. Initialize agent
        agent = SummaryAgent()
        
        # 2. Verify agent configuration
        assert agent.mode == "SAFE_TEST", f"Expected mode=SAFE_TEST, got {agent.mode}"
        assert agent.is_dry_run() is False, "Expected is_dry_run()=False"
        assert "19699862097" in agent.allowed_test_pages, "Page should be in whitelist"
        
        print(f"\n[SAFE_TEST] Agent configuration:")
        print(f"  Mode: {agent.mode}")
        print(f"  Dry-run: {agent.is_dry_run()}")
        print(f"  Whitelist: {agent.allowed_test_pages}")
        
        # 3. Get initial page state
        page_id = "19699862097"
        initial_page = await agent.confluence.get_page(page_id)
        initial_version = initial_page["version"]["number"]
        initial_length = len(initial_page["body"]["storage"]["value"])
        
        print(f"\n[SAFE_TEST] Initial page state:")
        print(f"  Version: {initial_version}")
        print(f"  Content length: {initial_length} chars")
        
        # 4. Call update_page_with_summary (should perform REAL update)
        print(f"\n[SAFE_TEST] Calling update_page_with_summary({page_id})...")
        result = await agent.update_page_with_summary(page_id)
        
        # 5. Verify updated result
        print(f"\n[SAFE_TEST] Result:")
        print(f"  Status: {result.get('status')}")
        print(f"  Summary added: {result.get('summary_added')}")
        
        assert result["status"] == "updated", f"Expected status=updated, got {result.get('status')}"
        assert result["summary_added"] is True, "Expected summary_added=True"
        assert "page_id" in result, "Expected page_id in result"
        assert "summary_tokens_estimate" in result, "Expected token estimate"
        
        # 6. Verify page WAS modified
        final_page = await agent.confluence.get_page(page_id)
        final_version = final_page["version"]["number"]
        final_length = len(final_page["body"]["storage"]["value"])
        
        print(f"\n[SAFE_TEST] Final page state:")
        print(f"  Version: {final_version}")
        print(f"  Content length: {final_length} chars")
        
        assert final_version > initial_version, \
            f"Page version should increase ({initial_version} → {final_version})"
        assert final_length > initial_length, \
            f"Content length should increase ({initial_length} → {final_length})"
        
        # 7. Verify summary was generated
        assert result.get("summary_tokens_estimate") > 0, "Summary should have been generated"
        print(f"[SAFE_TEST] ✅ Summary generated ({result.get('summary_tokens_estimate')} tokens)")
        
        print(f"\n[SAFE_TEST] ✅ All assertions passed!")
        print(f"[SAFE_TEST] ✅ Real update behavior confirmed:")
        print(f"  - Whitelisted page allowed")
        print(f"  - Summary generated via OpenAI")
        print(f"  - Page UPDATED in Confluence")
        print(f"  - Updated status returned")
        print(f"  - Version incremented: {initial_version} → {final_version}")
        print(f"  - Content increased: {initial_length} → {final_length} chars")
        
    finally:
        # Restore original environment
        if original_mode:
            os.environ["SUMMARY_AGENT_MODE"] = original_mode
        else:
            os.environ.pop("SUMMARY_AGENT_MODE", None)


if __name__ == "__main__":
    # Run tests manually
    print("="*80)
    print("SUMMARYAGENT DRY-RUN TEST FOR WHITELISTED PAGE")
    print("="*80)
    
    asyncio.run(test_summary_agent_dry_run_for_whitelisted_page())
    print("\n" + "="*80)
    
    asyncio.run(test_summary_agent_blocks_non_whitelisted_page_in_test_mode())
    print("="*80)
    
    print("\n" + "="*80)
    print("SUMMARYAGENT SAFE_TEST MODE TEST")
    print("="*80)
    asyncio.run(test_summary_agent_safe_test_allows_update())
    print("="*80)
