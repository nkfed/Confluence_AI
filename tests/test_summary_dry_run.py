"""
Test SummaryAgent dry-run behavior in TEST mode
"""
import asyncio
import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from src.agents.summary_agent import SummaryAgent
from src.core.logging.logging_config import configure_logging

configure_logging()

async def test_dry_run_in_test_mode():
    print("="*80)
    print("SUMMARYAGENT DRY-RUN TEST (TEST MODE)")
    print("="*80)
    
    # Check configuration
    print("\n1. Configuration:")
    print(f"   SUMMARY_AGENT_MODE = {os.getenv('SUMMARY_AGENT_MODE')}")
    print(f"   SUMMARY_AGENT_TEST_PAGE = {os.getenv('SUMMARY_AGENT_TEST_PAGE')}")
    
    # Initialize agent
    print("\n2. Initializing SummaryAgent...")
    agent = SummaryAgent()
    print(f"   Agent mode: {agent.mode}")
    print(f"   Allowed pages: {agent.allowed_test_pages}")
    
    # Test with whitelisted page
    page_id = "19699862097"
    print(f"\n3. Testing update_page_with_summary for page {page_id}...")
    print(f"   Page is in whitelist: {page_id in agent.allowed_test_pages}")
    
    # Get initial page state
    initial_page = await agent.confluence.get_page(page_id)
    initial_version = initial_page["version"]["number"]
    initial_length = len(initial_page["body"]["storage"]["value"])
    
    print(f"   Initial page version: {initial_version}")
    print(f"   Initial content length: {initial_length} chars")
    
    # Call update_page_with_summary
    print("\n4. Calling update_page_with_summary...")
    result = await agent.update_page_with_summary(page_id)
    
    print(f"\n5. Result:")
    print(f"   Status: {result.get('status')}")
    print(f"   Summary added: {result.get('summary_added')}")
    print(f"   Message: {result.get('message', 'N/A')}")
    
    # Check if page was actually updated
    print("\n6. Verifying Confluence state...")
    final_page = await agent.confluence.get_page(page_id)
    final_version = final_page["version"]["number"]
    final_length = len(final_page["body"]["storage"]["value"])
    
    print(f"   Final page version: {final_version}")
    print(f"   Final content length: {final_length} chars")
    
    # Verification
    print("\n7. Verification:")
    if result.get('status') == 'dry_run':
        print("   [OK] Status is 'dry_run'")
    else:
        print(f"   [FAIL] Status is '{result.get('status')}', expected 'dry_run'")
    
    if not result.get('summary_added'):
        print("   [OK] summary_added is False")
    else:
        print("   [FAIL] summary_added is True, expected False")
    
    if initial_version == final_version:
        print(f"   [OK] Page version unchanged ({initial_version})")
    else:
        print(f"   [FAIL] Page version changed ({initial_version} -> {final_version})")
    
    if initial_length == final_length:
        print(f"   [OK] Content length unchanged ({initial_length} chars)")
    else:
        print(f"   [FAIL] Content length changed ({initial_length} -> {final_length} chars)")
    
    print("\n" + "="*80)
    if (result.get('status') == 'dry_run' and 
        not result.get('summary_added') and 
        initial_version == final_version and 
        initial_length == final_length):
        print("[SUCCESS] TEST MODE DRY-RUN WORKS CORRECTLY")
        print("Summary generated but NOT written to Confluence")
    else:
        print("[FAILURE] TEST MODE IS NOT WORKING")
        print("Page was updated when it shouldn't be")
    print("="*80)

if __name__ == "__main__":
    asyncio.run(test_dry_run_in_test_mode())
