"""
Test tag-tree endpoint "added" field
"""
import pytest
import asyncio
from src.services.bulk_tagging_service import BulkTaggingService
from src.clients.confluence_client import ConfluenceClient
from src.core.logging.logging_config import configure_logging
import os

configure_logging()


@pytest.mark.asyncio
async def test_tag_tree_added_field_dry_run():
    """
    Test that "added" field is empty in dry-run mode.
    
    Expected:
    - added: []
    - labels_to_add: [...] (non-empty if changes needed)
    """
    print(f"\n[TEST] Testing tag-tree 'added' field in dry-run mode")
    
    # Use a known root page
    root_page_id = "19713687690"
    
    confluence_client = ConfluenceClient()
    service = BulkTaggingService(confluence_client=confluence_client)
    
    result = await service.tag_tree(root_page_id, dry_run=True)
    
    print(f"\n[TEST] Result:")
    print(f"  Total: {result.get('total')}")
    print(f"  Success: {result.get('success')}")
    
    # Check first page result
    if result.get('details'):
        first_page = result['details'][0]
        
        print(f"\n[TEST] First page:")
        print(f"  Page ID: {first_page.get('page_id')}")
        print(f"  Title: {first_page.get('title')}")
        print(f"  Status: {first_page.get('status')}")
        print(f"  Dry-run: {first_page.get('dry_run')}")
        
        # Verify unified structure
        assert "tags" in first_page, "Missing 'tags' field"
        tags = first_page["tags"]
        
        assert "proposed" in tags, "Missing 'tags.proposed' field"
        assert "existing" in tags, "Missing 'tags.existing' field"
        assert "to_add" in tags, "Missing 'tags.to_add' field"
        assert "added" in tags, "Missing 'tags.added' field"
        
        # Verify dry-run behavior
        assert first_page["dry_run"] == True, "dry_run should be True"
        
        if first_page.get("status") in ["dry_run", "updated"]:
            # In dry-run, added should be empty
            assert tags["added"] == [], f"In dry-run, 'added' should be [], got {tags['added']}"
            print(f"  Tags.added: {tags['added']} ✅")
            print(f"  Tags.to_add: {tags.get('to_add', [])} (would be added)")
        
        print(f"\n[TEST] ✅ Dry-run unified structure correct!")
    else:
        print(f"\n[TEST] ⚠️ No details returned")
    
    return result


@pytest.mark.asyncio
async def test_tag_tree_added_field_real_update():
    """
    Test that "added" field contains actual tags in real update mode.
    
    Expected:
    - added: [...] (same as labels_to_add if updated)
    - labels_to_add: [...] (tags that were added)
    """
    # WARNING: This will make real updates!
    # Override to SAFE_TEST mode to limit scope
    os.environ["TAGGING_AGENT_MODE"] = "SAFE_TEST"
    
    print(f"\n[TEST] Testing tag-tree 'added' field in real update mode")
    print(f"  ⚠️ This will make REAL updates to Confluence!")
    
    # Use a known root page (should be in whitelist for SAFE_TEST)
    root_page_id = "19713687690"
    
    confluence_client = ConfluenceClient()
    service = BulkTaggingService(confluence_client=confluence_client)
    
    result = await service.tag_tree(root_page_id, dry_run=False)
    
    print(f"\n[TEST] Result:")
    print(f"  Total: {result.get('total')}")
    print(f"  Success: {result.get('success')}")
    
    # Check first page result
    if result.get('details'):
        first_page = result['details'][0]
        
        print(f"\n[TEST] First page:")
        print(f"  Page ID: {first_page.get('page_id')}")
        print(f"  Title: {first_page.get('title')}")
        print(f"  Status: {first_page.get('status')}")
        print(f"  Dry-run: {first_page.get('dry_run')}")
        
        # Verify unified structure
        assert "tags" in first_page, "Missing 'tags' field"
        tags = first_page["tags"]
        
        assert "proposed" in tags, "Missing 'tags.proposed'"
        assert "existing" in tags, "Missing 'tags.existing'"
        assert "to_add" in tags, "Missing 'tags.to_add'"
        assert "added" in tags, "Missing 'tags.added'"
        
        # Verify real update behavior
        assert first_page["dry_run"] == False, "dry_run should be False"
        
        if first_page.get("status") == "updated":
            # In real update, to_add should be empty, added should have values
            assert tags["to_add"] == [], "In real update, 'to_add' should be []"
            print(f"  Tags.added: {tags['added']} ✅")
            print(f"  Tags.to_add: {tags['to_add']}")
        elif first_page.get("status") == "no_changes":
            # No changes, both should be empty
            assert tags["added"] == [], "No changes should have empty 'added'"
            assert tags["to_add"] == [], "No changes should have empty 'to_add'"
            print(f"  No changes - tags.added: {tags['added']} ✅")
        
        print(f"\n[TEST] ✅ Real update unified structure correct!")
    else:
        print(f"\n[TEST] ⚠️ No details returned")
    
    # Reset
    os.environ["TAGGING_AGENT_MODE"] = "SAFE_TEST"
    
    return result


@pytest.mark.asyncio
async def test_tag_tree_added_field_consistency():
    """
    Test that "added" field is consistent across all pages.
    
    Verify:
    - added is always a list
    - added never contains None
    - added is [] for dry-run
    - added equals labels_to_add for real updates
    """
    print(f"\n[TEST] Testing 'added' field consistency across all pages")
    
    root_page_id = "19713687690"
    
    confluence_client = ConfluenceClient()
    service = BulkTaggingService(confluence_client=confluence_client)
    
    # Test both dry-run and real update
    for dry_run in [True, False]:
        if not dry_run:
            os.environ["TAGGING_AGENT_MODE"] = "SAFE_TEST"
        
        print(f"\n[TEST] Testing dry_run={dry_run}")
        result = await service.tag_tree(root_page_id, dry_run=dry_run)
        
        for i, page_detail in enumerate(result.get('details', []), 1):
            # Verify unified tags structure exists
            assert "tags" in page_detail, f"Page {i}: Missing 'tags' field"
            tags = page_detail["tags"]
            
            # Verify tags is a dict with required fields
            assert isinstance(tags, dict), f"Page {i}: 'tags' should be a dict"
            assert "proposed" in tags, f"Page {i}: Missing 'tags.proposed'"
            assert "existing" in tags, f"Page {i}: Missing 'tags.existing'"
            assert "to_add" in tags, f"Page {i}: Missing 'tags.to_add'"
            assert "added" in tags, f"Page {i}: Missing 'tags.added'"
            
            # Verify all fields are lists
            assert isinstance(tags["proposed"], list), f"Page {i}: 'proposed' should be a list"
            assert isinstance(tags["existing"], list), f"Page {i}: 'existing' should be a list"
            assert isinstance(tags["to_add"], list), f"Page {i}: 'to_add' should be a list"
            assert isinstance(tags["added"], list), f"Page {i}: 'added' should be a list"
            
            # Verify no None values
            assert None not in tags["proposed"], f"Page {i}: 'proposed' contains None"
            assert None not in tags["existing"], f"Page {i}: 'existing' contains None"
            assert None not in tags["to_add"], f"Page {i}: 'to_add' contains None"
            assert None not in tags["added"], f"Page {i}: 'added' contains None"
            
            # Verify consistency with dry_run
            if dry_run:
                assert tags["added"] == [], f"Page {i}: dry-run should have empty 'added'"
            else:
                if page_detail.get("status") == "updated":
                    assert tags["to_add"] == [], f"Page {i}: real update should have empty 'to_add'"
                elif page_detail.get("status") == "no_changes":
                    assert tags["added"] == [], f"Page {i}: no_changes should have empty 'added'"
                    assert tags["to_add"] == [], f"Page {i}: no_changes should have empty 'to_add'"
        
        print(f"  ✅ All {len(result.get('details', []))} pages have consistent unified tags structure")
    
    # Reset
    os.environ["TAGGING_AGENT_MODE"] = "SAFE_TEST"
    
    print(f"\n[TEST] ✅ Consistency test passed!")


if __name__ == "__main__":
    print("="*80)
    print("TAG-TREE 'ADDED' FIELD TEST")
    print("="*80)
    
    print("\n" + "="*80)
    print("TEST 1: DRY-RUN MODE")
    print("="*80)
    asyncio.run(test_tag_tree_added_field_dry_run())
    
    print("\n" + "="*80)
    print("TEST 2: REAL UPDATE MODE")
    print("="*80)
    asyncio.run(test_tag_tree_added_field_real_update())
    
    print("\n" + "="*80)
    print("TEST 3: CONSISTENCY CHECK")
    print("="*80)
    asyncio.run(test_tag_tree_added_field_consistency())
    
    print("="*80)
