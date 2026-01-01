"""
Comprehensive test for unified tag structure across all endpoints
"""
import pytest
import asyncio
from src.services.tagging_service import TaggingService
from src.services.bulk_tagging_service import BulkTaggingService
from src.clients.confluence_client import ConfluenceClient
from src.core.logging.logging_config import configure_logging

configure_logging()


def verify_unified_tags_structure(tags: dict, context: str):
    """
    Verify that tags follow the unified structure:
    {
        "proposed": [...],
        "existing": [...],
        "to_add": [...],
        "added": [...]
    }
    """
    assert tags is not None, f"{context}: tags should not be None"
    assert isinstance(tags, dict), f"{context}: tags should be a dict"
    
    # Verify required fields
    assert "proposed" in tags, f"{context}: Missing 'proposed'"
    assert "existing" in tags, f"{context}: Missing 'existing'"
    assert "to_add" in tags, f"{context}: Missing 'to_add'"
    assert "added" in tags, f"{context}: Missing 'added'"
    
    # Verify all are lists
    assert isinstance(tags["proposed"], list), f"{context}: 'proposed' should be list"
    assert isinstance(tags["existing"], list), f"{context}: 'existing' should be list"
    assert isinstance(tags["to_add"], list), f"{context}: 'to_add' should be list"
    assert isinstance(tags["added"], list), f"{context}: 'added' should be list"
    
    # Verify no None values
    assert None not in tags["proposed"], f"{context}: 'proposed' contains None"
    assert None not in tags["existing"], f"{context}: 'existing' contains None"
    assert None not in tags["to_add"], f"{context}: 'to_add' contains None"
    assert None not in tags["added"], f"{context}: 'added' contains None"
    
    print(f"  ✅ {context}: Unified structure verified")


@pytest.mark.asyncio
async def test_unified_structure_auto_tag():
    """
    Test /pages/{page_id}/auto-tag endpoint
    """
    print(f"\n[TEST] Testing /pages/{{page_id}}/auto-tag unified structure")
    
    page_id = "19713687690"
    
    service = TaggingService()
    
    # Test dry-run
    result = await service.auto_tag_page(page_id, dry_run=True)
    print(f"  Status: {result.get('status')}")
    
    if result.get("status") in ["dry_run", "updated"]:
        verify_unified_tags_structure(result["tags"], "/auto-tag (dry-run)")
        
        # Verify dry-run logic
        tags = result["tags"]
        assert tags["added"] == [], "/auto-tag dry-run should have empty 'added'"
    
    print(f"[TEST] ✅ /auto-tag unified structure correct!")


@pytest.mark.asyncio
async def test_unified_structure_bulk_tag_pages():
    """
    Test /bulk/tag-pages endpoint
    """
    print(f"\n[TEST] Testing /bulk/tag-pages unified structure")
    
    page_ids = ["19713687690"]
    
    confluence_client = ConfluenceClient()
    service = BulkTaggingService(confluence_client=confluence_client)
    
    # Test dry-run
    result = await service.tag_pages(page_ids, space_key="euheals", dry_run=True)
    
    print(f"  Total: {result.get('total')}")
    print(f"  Success: {result.get('success')}")
    
    for i, detail in enumerate(result.get('details', []), 1):
        if detail.get("status") in ["dry_run", "updated"]:
            verify_unified_tags_structure(detail["tags"], f"/bulk/tag-pages page {i}")
            
            # Verify dry-run logic
            tags = detail["tags"]
            assert tags["added"] == [], f"Page {i} dry-run should have empty 'added'"
    
    print(f"[TEST] ✅ /bulk/tag-pages unified structure correct!")


@pytest.mark.asyncio
async def test_unified_structure_bulk_tag_tree():
    """
    Test /bulk/tag-tree endpoint
    """
    print(f"\n[TEST] Testing /bulk/tag-tree unified structure")
    
    root_page_id = "19713687690"
    
    confluence_client = ConfluenceClient()
    service = BulkTaggingService(confluence_client=confluence_client)
    
    # Test dry-run
    result = await service.tag_tree(space_key="euheals", root_page_id=root_page_id, dry_run=True)
    
    print(f"  Total: {result.get('total')}")
    print(f"  Success: {result.get('success')}")
    
    for i, detail in enumerate(result.get('details', []), 1):
        if detail.get("status") in ["dry_run", "updated", "no_changes"]:
            verify_unified_tags_structure(detail["tags"], f"/bulk/tag-tree page {i}")
            
            # Verify dry-run logic
            tags = detail["tags"]
            assert tags["added"] == [], f"Page {i} dry-run should have empty 'added'"
    
    print(f"[TEST] ✅ /bulk/tag-tree unified structure correct!")


@pytest.mark.asyncio
async def test_unified_structure_consistency():
    """
    Test that all endpoints use exactly the same structure
    """
    print(f"\n[TEST] Testing unified structure consistency across all endpoints")
    
    page_id = "19713687690"
    
    # Get results from all endpoints
    tagging_service = TaggingService()
    confluence_client = ConfluenceClient()
    bulk_service = BulkTaggingService(confluence_client=confluence_client)
    
    print(f"\n  Fetching from /auto-tag...")
    auto_tag_result = await tagging_service.auto_tag_page(page_id, dry_run=True)
    
    print(f"  Fetching from /bulk/tag-pages...")
    bulk_pages_result = await bulk_service.tag_pages([page_id], space_key="euheals", dry_run=True)
    
    print(f"  Fetching from /bulk/tag-tree...")
    bulk_tree_result = await bulk_service.tag_tree(space_key="euheals", root_page_id=page_id, dry_run=True)
    
    # Verify all have tags structure
    assert "tags" in auto_tag_result, "/auto-tag missing 'tags'"
    assert "tags" in bulk_pages_result["details"][0], "/bulk/tag-pages missing 'tags'"
    assert "tags" in bulk_tree_result["details"][0], "/bulk/tag-tree missing 'tags'"
    
    # Get tags from each endpoint
    tags_auto = auto_tag_result["tags"]
    tags_bulk_pages = bulk_pages_result["details"][0]["tags"]
    tags_bulk_tree = bulk_tree_result["details"][0]["tags"]
    
    # Verify all have same keys
    expected_keys = {"proposed", "existing", "to_add", "added"}
    
    assert set(tags_auto.keys()) == expected_keys, f"/auto-tag has different keys: {set(tags_auto.keys())}"
    assert set(tags_bulk_pages.keys()) == expected_keys, f"/bulk/tag-pages has different keys: {set(tags_bulk_pages.keys())}"
    assert set(tags_bulk_tree.keys()) == expected_keys, f"/bulk/tag-tree has different keys: {set(tags_bulk_tree.keys())}"
    
    print(f"\n  ✅ All endpoints use identical structure:")
    print(f"     - proposed")
    print(f"     - existing")
    print(f"     - to_add")
    print(f"     - added")
    
    print(f"\n[TEST] ✅ Unified structure consistency verified across all endpoints!")


if __name__ == "__main__":
    print("="*80)
    print("UNIFIED TAG STRUCTURE - COMPREHENSIVE TEST")
    print("="*80)
    
    print("\n" + "="*80)
    print("TEST 1: /pages/{page_id}/auto-tag")
    print("="*80)
    asyncio.run(test_unified_structure_auto_tag())
    
    print("\n" + "="*80)
    print("TEST 2: /bulk/tag-pages")
    print("="*80)
    asyncio.run(test_unified_structure_bulk_tag_pages())
    
    print("\n" + "="*80)
    print("TEST 3: /bulk/tag-tree")
    print("="*80)
    asyncio.run(test_unified_structure_bulk_tag_tree())
    
    print("\n" + "="*80)
    print("TEST 4: CONSISTENCY CHECK")
    print("="*80)
    asyncio.run(test_unified_structure_consistency())
    
    print("\n" + "="*80)
    print("✅ ALL UNIFIED STRUCTURE TESTS PASSED!")
    print("="*80)
