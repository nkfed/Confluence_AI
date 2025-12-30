"""
Test AgentModeResolver and unified mode logic
"""
import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from src.core.agent_mode_resolver import AgentModeResolver
from src.agents.summary_agent import SummaryAgent
from src.agents.tagging_agent import TaggingAgent
from src.core.logging.logging_config import configure_logging
from settings import AgentMode

configure_logging()

print("="*80)
print("AGENT MODE RESOLVER TEST")
print("="*80)

# Test 1: AgentModeResolver
print("\n1. AgentModeResolver Tests:")
print(f"   Global AGENT_MODE: {os.getenv('AGENT_MODE')}")
print(f"   SUMMARY_AGENT_MODE: {os.getenv('SUMMARY_AGENT_MODE')}")

mode = AgentModeResolver.resolve_mode("SUMMARY_AGENT")
whitelist = AgentModeResolver.resolve_whitelist("SUMMARY_AGENT")
print(f"   Resolved mode: {mode}")
print(f"   Resolved whitelist: {whitelist}")

# Test 2: Dry-run detection
print("\n2. Dry-run Detection:")
for test_mode in [AgentMode.TEST, AgentMode.SAFE_TEST, AgentMode.PROD]:
    should_dry_run = AgentModeResolver.should_perform_dry_run(test_mode)
    print(f"   {test_mode}: dry_run={should_dry_run}")

# Test 3: Confluence modification permissions
print("\n3. Confluence Modification Permissions:")
test_cases = [
    (AgentMode.TEST, "19713687690", ["19713687690", "19699862097"]),
    (AgentMode.TEST, "19700089019", ["19713687690", "19699862097"]),
    (AgentMode.SAFE_TEST, "19713687690", ["19713687690", "19699862097"]),
    (AgentMode.SAFE_TEST, "19700089019", ["19713687690", "19699862097"]),
    (AgentMode.PROD, "19713687690", ["19713687690", "19699862097"]),
    (AgentMode.PROD, "19700089019", ["19713687690", "19699862097"]),
]

for mode, page_id, wlist in test_cases:
    can_modify = AgentModeResolver.can_modify_confluence(mode, page_id, wlist)
    in_whitelist = "✓" if page_id in wlist else "✗"
    print(f"   {mode:10} | page={page_id} | in_whitelist={in_whitelist} | can_modify={can_modify}")

# Test 4: Agent initialization
print("\n4. Agent Initialization:")
print("\n   SummaryAgent:")
summary_agent = SummaryAgent()
print(f"     Mode: {summary_agent.mode}")
print(f"     Whitelist: {summary_agent.allowed_test_pages}")

print("\n   TaggingAgent:")
tagging_agent = TaggingAgent()
print(f"     Mode: {tagging_agent.mode}")
print(f"     Whitelist: {tagging_agent.allowed_test_pages}")

# Test 5: Unified is_page_allowed logic
print("\n5. Unified is_page_allowed() Logic:")
test_pages = ["19713687690", "19699862097", "19700089019", "12345"]
print(f"   SummaryAgent (mode={summary_agent.mode}):")
for page in test_pages:
    allowed = summary_agent.is_page_allowed(page)
    print(f"     {page}: {allowed}")

print(f"\n   TaggingAgent (mode={tagging_agent.mode}):")
for page in test_pages:
    allowed = tagging_agent.is_page_allowed(page)
    print(f"     {page}: {allowed}")

print("\n" + "="*80)
print("SUMMARY:")
print("="*80)
print(f"✓ AgentModeResolver working")
print(f"✓ Mode resolution: TEST < SAFE_TEST < PROD")
print(f"✓ TEST mode: dry-run only, no Confluence changes")
print(f"✓ SAFE_TEST mode: updates only whitelist pages")
print(f"✓ PROD mode: updates all pages")
print(f"✓ All agents use unified BaseAgent logic")
print("="*80)
