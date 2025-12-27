"""
Test auto-tag endpoint with dry_run parameter
"""
import pytest
import asyncio
from src.services.tagging_service import TaggingService, flatten_tags
from src.core.logging.logging_config import configure_logging

configure_logging()


def test_flatten_tags():
    """
    Test that flatten_tags correctly converts dict to flat list
    """
    tag_dict = {
        "doc": ["doc-tech", "doc-architecture"],
        "domain": ["domain-helpdesk-site"],
        "kb": ["kb-canonical", "kb-overview"],
        "tool": ["tool-rovo-agent"]
    }
    
    result = flatten_tags(tag_dict)
    
    print(f"\n[TEST] Input: {tag_dict}")
    print(f"[TEST] Output: {result}")
    
    # Should be flat list
    assert isinstance(result, list), "Result should be a list"
    
    # Should contain all tags
    expected_tags = [
        "doc-tech", "doc-architecture",
        "domain-helpdesk-site",
        "kb-canonical", "kb-overview",
        "tool-rovo-agent"
    ]
    assert len(result) == len(expected_tags), f"Expected {len(expected_tags)} tags, got {len(result)}"
    
    # All expected tags should be present
    for tag in expected_tags:
        assert tag in result, f"Expected tag '{tag}' not found in result"
    
    # No duplicates
    assert len(result) == len(set(result)), "Result should not contain duplicates"
    
    # No dict keys as values
    assert "doc" not in result, "Should not contain dict keys"
    assert "domain" not in result, "Should not contain dict keys"
    
    print(f"[TEST] ✅ Flatten function test passed!")


@pytest.mark.asyncio
async def test_auto_tag_with_dry_run_true():
    """
    Test that auto_tag_page with explicit dry_run=True:
    - Generates tags
    - Does NOT call update_labels()
    - Returns dry_run status
    """
    service = TaggingService()
    
    # Test with explicit dry_run=True
    result = await service.auto_tag_page("19713687690", dry_run=True)
    
    print(f"\n[TEST] Explicit dry-run result:")
    print(f"  Status: {result.get('status')}")
    print(f"  Tags added: {result.get('tags_added')}")
    print(f"  Tags: {result.get('tags')}")
    
    assert result["status"] == "dry_run", f"Expected status=dry_run, got {result.get('status')}"
    assert result["tags_added"] is False, "Expected tags_added=False"
    assert "tags" in result, "Expected tags in result"
    assert isinstance(result["tags"], dict), "Expected tags to be dict"
    
    print(f"[TEST] ✅ Explicit dry-run test passed!")


@pytest.mark.asyncio
async def test_auto_tag_with_agent_mode():
    """
    Test that auto_tag_page with dry_run=None uses agent mode:
    - TEST mode -> dry_run
    - Generates tags
    - Does NOT call update_labels()
    """
    service = TaggingService()
    
    # Agent is in TEST mode (from .env)
    assert service.agent.mode == "TEST", f"Expected TEST mode, got {service.agent.mode}"
    assert service.agent.is_dry_run() is True, "Expected is_dry_run()=True"
    
    # Test with dry_run=None (should use agent mode)
    result = await service.auto_tag_page("19713687690", dry_run=None)
    
    print(f"\n[TEST] Agent mode result:")
    print(f"  Agent mode: {service.agent.mode}")
    print(f"  Status: {result.get('status')}")
    print(f"  Tags added: {result.get('tags_added')}")
    
    assert result["status"] == "dry_run", f"Expected status=dry_run from TEST mode, got {result.get('status')}"
    assert result["tags_added"] is False, "Expected tags_added=False"
    
    print(f"[TEST] ✅ Agent mode test passed!")


@pytest.mark.asyncio
async def test_auto_tag_with_dry_run_false():
    """
    Test that auto_tag_page with explicit dry_run=False:
    - Generates tags
    - Calls enforce_page_policy()
    - Updates whitelisted pages in TEST mode (allowed for access)
    """
    service = TaggingService()
    
    # Test with whitelisted page and explicit dry_run=False
    result = await service.auto_tag_page("19713687690", dry_run=False)
    
    print(f"\n[TEST] Explicit update result:")
    print(f"  Agent mode: {service.agent.mode}")
    print(f"  Status: {result.get('status')}")
    print(f"  Tags added: {result.get('tags_added')}")
    
    # In TEST mode with whitelisted page:
    # - enforce_page_policy allows ACCESS (page in whitelist)
    # - but dry_run=False overrides agent mode
    # - so update happens
    assert result["status"] == "updated", f"Expected status=updated, got {result.get('status')}"
    assert result["tags_added"] is True, "Expected tags_added=True"
    assert "tags" in result, "Expected tags in result"
    assert isinstance(result["tags"], dict), "Expected tags to be dict"
    
    print(f"[TEST] ✅ Explicit override test passed!")


if __name__ == "__main__":
    print("="*80)
    print("AUTO-TAG DRY-RUN TEST")
    print("="*80)
    
    asyncio.run(test_auto_tag_with_dry_run_true())
    print("\n" + "="*80)
    
    asyncio.run(test_auto_tag_with_dry_run_false())
    print("="*80)
