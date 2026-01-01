"""
Test ConfluenceClient.append_to_page coroutine fix
"""
import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from src.clients.confluence_client import ConfluenceClient


class TestConfluenceClientAsync:
    """Test async methods in ConfluenceClient"""
    
    @pytest.mark.asyncio
    async def test_get_page_returns_dict_with_body(self):
        """Test that get_page returns proper structure"""
        client = ConfluenceClient()
        page_id = "19699862097"
        
        page = await client.get_page(page_id)
        
        # Verify page structure
        assert isinstance(page, dict), "Page should be a dict"
        assert "body" in page, "Page should have 'body' key"
        assert "storage" in page["body"], "Page body should have 'storage' key"
        assert "value" in page["body"]["storage"], "Storage should have 'value' key"
        assert isinstance(page["body"]["storage"]["value"], str), "Body value should be string"
        
        print(f"[OK] Page structure is correct")
        print(f"   Body length: {len(page['body']['storage']['value'])} chars")
    
    @pytest.mark.asyncio
    async def test_append_to_page_awaits_correctly(self):
        """Test that append_to_page properly awaits get_page"""
        client = ConfluenceClient()
        page_id = "19699862097"
        html_block = "<p>Test block from pytest</p>"
        
        try:
            # This should NOT raise TypeError about coroutine
            result = await client.append_to_page(page_id, html_block)
            
            assert isinstance(result, dict), "Result should be a dict"
            print(f"[OK] append_to_page executed without coroutine error")
            print(f"   Result keys: {list(result.keys())}")
            
        except TypeError as e:
            if "coroutine" in str(e).lower() or "subscriptable" in str(e).lower():
                pytest.fail(f"Coroutine misuse detected: {e}")
            else:
                raise


class TestSummaryAgentAsync:
    """Test async methods in SummaryAgent"""
    
    @pytest.mark.asyncio
    async def test_summary_is_appended_to_page(self):
        """Test that summary is actually written to Confluence"""
        from src.agents.summary_agent import SummaryAgent
        import os
        
        # Set PROD mode for actual update test
        os.environ["SUMMARY_AGENT_MODE"] = "PROD"
        
        agent = SummaryAgent()
        page_id = "19699862097"
        
        print(f"\n[TEST] Testing summary append to page {page_id}")
        print(f"[TEST] Agent mode: {agent.mode}")
        
        # Get initial page state
        page_before = await agent.confluence.get_page(page_id)
        html_before = page_before["body"]["storage"]["value"]
        version_before = page_before["version"]["number"]
        
        print(f"   Initial version: {version_before}")
        print(f"   Initial content length: {len(html_before)} chars")
        
        # Update page with summary
        result = await agent.update_page_with_summary(page_id)
        
        print(f"   Update result: {result}")
        
        # Get updated page state
        page_after = await agent.confluence.get_page(page_id)
        html_after = page_after["body"]["storage"]["value"]
        version_after = page_after["version"]["number"]
        
        print(f"   After version: {version_after}")
        print(f"   After content length: {len(html_after)} chars")
        
        # Verify summary was added (or in dry-run mode, check for dry_run status)
        if result.get("status") == "dry_run":
            print(f"[OK] Summary in dry-run mode (not actually appended)")
        else:
            # PROD mode: summary should be added
            assert "<h2>AI Summary</h2>" in html_after, "Summary header should be in page"
            assert version_after > version_before, "Version should be incremented"
            assert len(html_after) > len(html_before), "Content should be longer"
            print(f"[OK] Summary successfully appended to page")
        
        # Reset environment
        os.environ["SUMMARY_AGENT_MODE"] = "TEST"


if __name__ == "__main__":
    # Run tests manually
    async def main():
        print("="*80)
        print("CONFLUENCE CLIENT ASYNC TEST")
        print("="*80)
        
        test = TestConfluenceClientAsync()
        
        print("\n1. Testing get_page structure...")
        try:
            await test.test_get_page_returns_dict_with_body()
        except Exception as e:
            print(f"[FAIL] {e}")
            import traceback
            traceback.print_exc()
        
        print("\n2. Testing append_to_page coroutine handling...")
        try:
            await test.test_append_to_page_awaits_correctly()
        except Exception as e:
            print(f"[FAIL] {e}")
            import traceback
            traceback.print_exc()
        
        print("\n3. Testing SummaryAgent.update_page_with_summary...")
        try:
            summary_test = TestSummaryAgentAsync()
            await summary_test.test_summary_is_appended_to_page()
        except Exception as e:
            print(f"[FAIL] {e}")
            import traceback
            traceback.print_exc()
        
        print("\n" + "="*80)
        print("[OK] ALL TESTS COMPLETE")
        print("="*80)
    
    asyncio.run(main())
