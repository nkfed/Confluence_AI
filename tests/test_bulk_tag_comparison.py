"""
Test bulk tagging with tag comparison
"""
import pytest
import asyncio
from src.services.bulk_tagging_service import BulkTaggingService, flatten_tags
from src.core.logging.logging_config import configure_logging

configure_logging()


def test_flatten_tags_in_bulk():
    """Test that flatten_tags works correctly in bulk context"""
    tag_dict = {
        "doc": ["doc-tech"],
        "domain": ["domain-helpdesk-site"],
        "kb": ["kb-canonical"],
        "tool": []
    }
    
    result = flatten_tags(tag_dict)
    
    assert isinstance(result, list)
    assert "doc-tech" in result
    assert "domain-helpdesk-site" in result
    assert "kb-canonical" in result
    assert len(result) == 3
    
    print(f"[TEST] ✅ Flatten in bulk context works!")


@pytest.mark.asyncio
async def test_bulk_tag_pages_dry_run():
    """
    Test bulk tagging with dry_run=True
    - Respects dry_run flag
    - Returns tag comparison (proposed, existing, to_add)
    - Does not update Confluence
    """
    service = BulkTaggingService()
    
    # Test with 2 whitelisted pages in dry_run mode
    page_ids = ["19713687690", "19699862097"]
    
    print(f"\n[TEST] Bulk tagging {len(page_ids)} pages with dry_run=True")
    
    result = await service.tag_pages(page_ids, dry_run=True)
    
    print(f"\n[TEST] Result:")
    print(f"  Total: {result.get('total')}")
    print(f"  Processed: {result.get('processed')}")
    print(f"  Success: {result.get('success')}")
    print(f"  Dry-run: {result.get('dry_run')}")
    
    assert result["dry_run"] is True, "Expected dry_run=True"
    assert result["total"] == 2, "Expected 2 pages"
    assert result["success"] >= 0, "Expected success count"
    
    # Check details
    for detail in result["details"]:
        print(f"\n[TEST] Page {detail['page_id']}:")
        print(f"  Status: {detail['status']}")
        
        if detail["status"] == "dry_run":
            tags = detail.get("tags", {})
            print(f"  Proposed: {len(tags.get('proposed', []))} tags")
            print(f"  Existing: {len(tags.get('existing', []))} tags")
            print(f"  To add: {len(tags.get('to_add', []))} tags")
            
            # Verify structure
            assert "proposed" in tags, "Expected 'proposed' in tags"
            assert "existing" in tags, "Expected 'existing' in tags"
            assert "to_add" in tags, "Expected 'to_add' in dry_run"
            assert isinstance(tags["proposed"], list), "proposed should be list"
            assert isinstance(tags["existing"], list), "existing should be list"
            assert isinstance(tags["to_add"], list), "to_add should be list"
    
    print(f"\n[TEST] ✅ Bulk dry-run test passed!")


@pytest.mark.asyncio
async def test_bulk_tag_pages_real_update():
    """
    Test bulk tagging with dry_run=False
    - Updates Confluence
    - Returns tag comparison
    - Shows added tags (not to_add)
    """
    service = BulkTaggingService()
    
    # Test with 1 whitelisted page
    page_ids = ["19713687690"]
    
    print(f"\n[TEST] Bulk tagging {len(page_ids)} pages with dry_run=False")
    
    result = await service.tag_pages(page_ids, dry_run=False)
    
    print(f"\n[TEST] Result:")
    print(f"  Total: {result.get('total')}")
    print(f"  Processed: {result.get('processed')}")
    print(f"  Success: {result.get('success')}")
    print(f"  Dry-run: {result.get('dry_run')}")
    
    assert result["dry_run"] is False, "Expected dry_run=False"
    assert result["total"] == 1, "Expected 1 page"
    
    # Check details
    for detail in result["details"]:
        print(f"\n[TEST] Page {detail['page_id']}:")
        print(f"  Status: {detail['status']}")
        
        if detail["status"] == "updated":
            tags = detail.get("tags", {})
            print(f"  Proposed: {tags.get('proposed', [])}")
            print(f"  Existing: {tags.get('existing', [])}")
            print(f"  Added: {tags.get('added', [])}")
            
            # Verify structure
            assert "proposed" in tags, "Expected 'proposed' in tags"
            assert "existing" in tags, "Expected 'existing' in tags"
            assert "added" in tags, "Expected 'added' in real update"
            assert "to_add" not in tags or tags["to_add"] == [], "Should not have 'to_add' in real update"
    
    print(f"\n[TEST] ✅ Bulk real update test passed!")


if __name__ == "__main__":
    print("="*80)
    print("BULK TAGGING TAG COMPARISON TEST")
    print("="*80)
    
    test_flatten_tags_in_bulk()
    
    print("\n" + "="*80)
    asyncio.run(test_bulk_tag_pages_dry_run())
    
    print("\n" + "="*80)
    asyncio.run(test_bulk_tag_pages_real_update())
    
    print("="*80)
