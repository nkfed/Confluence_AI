"""
Test agent mode configuration
"""
import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from src.agents.summary_agent import SummaryAgent
from src.agents.tagging_agent import TaggingAgent
from src.core.logging.logging_config import configure_logging

configure_logging()

print("="*80)
print("AGENT MODE CONFIGURATION TEST")
print("="*80)

# Test SummaryAgent
print("\n1. SummaryAgent Configuration:")
summary_agent = SummaryAgent()
print(f"   Mode: {summary_agent.mode}")
print(f"   Allowed test pages: {summary_agent.allowed_test_pages}")
print(f"   From .env SUMMARY_AGENT_MODE: {os.getenv('SUMMARY_AGENT_MODE')}")
print(f"   From .env SUMMARY_AGENT_TEST_PAGE: {os.getenv('SUMMARY_AGENT_TEST_PAGE')}")

# Test page access
test_page = "19713687690"
other_page = "19700089019"

print(f"\n2. Page Access Tests (mode={summary_agent.mode}):")
print(f"   is_page_allowed('{test_page}'): {summary_agent.is_page_allowed(test_page)}")
print(f"   is_page_allowed('{other_page}'): {summary_agent.is_page_allowed(other_page)}")

# Test TaggingAgent
print("\n3. TaggingAgent Configuration:")
tagging_agent = TaggingAgent()
print(f"   Mode: {tagging_agent.mode}")
print(f"   Allowed test pages: {tagging_agent.allowed_test_pages}")
print(f"   From .env TAGGING_AGENT_MODE: {os.getenv('TAGGING_AGENT_MODE')}")
print(f"   From .env TAGGING_AGENT_TEST_PAGE: {os.getenv('TAGGING_AGENT_TEST_PAGE')}")

# Test enforce_page_policy
print("\n4. Policy Enforcement Test:")
try:
    if summary_agent.mode == "TEST":
        print(f"   Testing enforcement for page {other_page} (should fail in TEST mode)")
        summary_agent.enforce_page_policy(other_page)
        print("   ❌ FAIL: Should have raised PermissionError")
    else:
        print(f"   Testing enforcement for page {other_page} (should pass in PROD mode)")
        summary_agent.enforce_page_policy(other_page)
        print("   ✅ PASS: Page allowed in PROD mode")
except PermissionError as e:
    print(f"   ✅ PASS: PermissionError raised as expected")
    print(f"   Error: {e}")

print("\n" + "="*80)
print("✅ CONFIGURATION TEST COMPLETE")
print("="*80)
