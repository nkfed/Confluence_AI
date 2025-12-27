"""
Test SummaryAgent mode configuration
"""
import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from src.agents.summary_agent import SummaryAgent
from src.core.logging.logging_config import configure_logging

configure_logging()

print("="*80)
print("SUMMARYAGENT MODE VERIFICATION TEST")
print("="*80)

# Test 1: Check .env configuration
print("\n1. Environment Configuration:")
print(f"   AGENT_MODE = {os.getenv('AGENT_MODE')}")
print(f"   SUMMARY_AGENT_MODE = {os.getenv('SUMMARY_AGENT_MODE')}")
print(f"   SUMMARY_AGENT_TEST_PAGE = {os.getenv('SUMMARY_AGENT_TEST_PAGE')}")

# Test 2: Initialize SummaryAgent (should print DEBUG messages)
print("\n2. Initializing SummaryAgent:")
agent = SummaryAgent()

# Test 3: Verify mode and whitelist
print("\n3. Agent Configuration:")
print(f"   Mode: {agent.mode}")
print(f"   Allowed test pages: {agent.allowed_test_pages}")
print(f"   Number of allowed pages: {len(agent.allowed_test_pages)}")

# Test 4: Test page access
print("\n4. Page Access Tests:")
test_cases = [
    ("19713687690", True, "In whitelist"),
    ("19699862097", True, "In whitelist"),
    ("19700089019", False, "NOT in whitelist"),
    ("12345", False, "Random page")
]

for page_id, should_allow, description in test_cases:
    is_allowed = agent.is_page_allowed(page_id)
    status = "[OK]" if is_allowed == should_allow else "[FAIL]"
    symbol = "YES" if is_allowed else "NO"
    print(f"   {status} Page {page_id} ({description}): {symbol}")

# Test 5: Test enforce_page_policy
print("\n5. Policy Enforcement Test:")
print("   Testing page NOT in whitelist (should raise PermissionError):")
try:
    agent.enforce_page_policy("19700089019")
    print("   [FAIL] No PermissionError raised!")
except PermissionError as e:
    print(f"   [OK] PermissionError raised as expected")
    print(f"   Error message: {str(e)[:100]}...")

print("\n   Testing page IN whitelist (should pass):")
try:
    agent.enforce_page_policy("19713687690")
    print("   [OK] Page allowed in whitelist")
except PermissionError as e:
    print(f"   [FAIL] Unexpected PermissionError: {e}")

print("\n" + "="*80)
print("VERIFICATION COMPLETE")
print("="*80)

print("\n" + "="*80)
print("EXPECTED BEHAVIOR IN TEST MODE:")
print("="*80)
print("1. SummaryAgent.mode = 'TEST'")
print("2. Only whitelisted pages can be updated")
print("3. Allowed pages: 19713687690, 19699862097")
print("4. Other pages will raise PermissionError")
print("5. Server logs should show: 'SUMMARY_AGENT initialized mode=TEST'")
print("="*80)
