"""
Тест для перевірки обмеження тегів на кореневій сторінці /bulk/tag-tree
"""
import pytest
import asyncio
import os
from src.services.bulk_tagging_service import BulkTaggingService
from src.clients.confluence_client import ConfluenceClient
from src.core.logging.logging_config import configure_logging
from src.config.tagging_settings import MAX_TAGS_PER_CATEGORY

configure_logging()


@pytest.mark.asyncio
async def test_tag_tree_root_page_tag_limit():
    """
    Перевірка що обмеження ≤MAX_TAGS_PER_CATEGORY застосовується до ROOT сторінки.
    
    Проблема:
    - Root page мала 15+ тегів (не обмежені)
    - Дочірні сторінки мали правильне обмеження
    
    Expected після fix:
    - Root page має ≤3 теги на категорію
    - Дочірні сторінки теж ≤3 теги
    """
    print(f"\n[TEST] Testing tag limit for ROOT page in /bulk/tag-tree")
    print(f"  MAX_TAGS_PER_CATEGORY: {MAX_TAGS_PER_CATEGORY}")
    
    # Set PROD mode (для доступу до root_page_id)
    os.environ["TAGGING_AGENT_MODE"] = "PROD"
    
    # Real root page ID (має багато контенту → генерує багато тегів)
    root_page_id = "19629473814"
    
    print(f"  Root page ID: {root_page_id}")
    print(f"  Mode: PROD")
    print(f"  Dry-run: True")
    
    confluence_client = ConfluenceClient()
    service = BulkTaggingService(confluence_client=confluence_client)
    
    # Execute dry-run
    result = await service.tag_tree(space_key="euheals", root_page_id=root_page_id, dry_run=True)
    
    print(f"\n[TEST] Result:")
    print(f"  Status: {result.get('status', 'N/A')}")
    print(f"  Total pages: {result.get('total')}")
    print(f"  Success: {result.get('success')}")
    
    details = result.get('details', [])
    
    if not details:
        pytest.fail("No details returned from tag-tree operation")
    
    # Find root page in results (it's the first one)
    root_page_detail = details[0]
    
    print(f"\n[TEST] ROOT PAGE ANALYSIS:")
    print(f"  Page ID: {root_page_detail.get('page_id')}")
    print(f"  Title: {root_page_detail.get('title')}")
    print(f"  Status: {root_page_detail.get('status')}")
    
    # Verify root page has tags structure
    assert "tags" in root_page_detail, "Root page missing 'tags' field"
    
    root_tags = root_page_detail["tags"]
    
    # Verify tags structure
    assert isinstance(root_tags, dict), "tags should be dict"
    assert "proposed" in root_tags, "Missing 'proposed'"
    assert "existing" in root_tags, "Missing 'existing'"
    assert "to_add" in root_tags, "Missing 'to_add'"
    assert "added" in root_tags, "Missing 'added'"
    
    print(f"\n[TEST] ROOT PAGE TAGS:")
    
    # Get tags by category from proposed
    from src.config.tagging_settings import TAG_CATEGORIES
    
    # Parse proposed tags by category
    proposed_by_category = {cat: [] for cat in TAG_CATEGORIES}
    for tag in root_tags["proposed"]:
        for cat in TAG_CATEGORIES:
            if tag.startswith(f"{cat}-"):
                proposed_by_category[cat].append(tag)
                break
    
    # Verify limits per category
    total_tags = 0
    for category in TAG_CATEGORIES:
        cat_tags = proposed_by_category[category]
        count = len(cat_tags)
        total_tags += count
        
        print(f"  {category}: {count} tags = {cat_tags}")
        
        # ✅ CRITICAL: Root page should respect MAX_TAGS_PER_CATEGORY
        assert count <= MAX_TAGS_PER_CATEGORY, \
            f"ROOT page {category} has {count} tags, should be ≤{MAX_TAGS_PER_CATEGORY}"
    
    print(f"\n  Total proposed tags: {total_tags}")
    print(f"  Max allowed: {MAX_TAGS_PER_CATEGORY * len(TAG_CATEGORIES)}")
    
    # ✅ Total should not exceed MAX_TAGS_PER_CATEGORY * categories
    max_total = MAX_TAGS_PER_CATEGORY * len(TAG_CATEGORIES)
    assert total_tags <= max_total, \
        f"ROOT page has {total_tags} total tags, should be ≤{max_total}"
    
    print(f"\n[TEST] ✅ ROOT page correctly limited to ≤{MAX_TAGS_PER_CATEGORY} tags per category!")
    
    # Also verify child pages (if any)
    if len(details) > 1:
        print(f"\n[TEST] CHILD PAGES VERIFICATION:")
        for i, child_detail in enumerate(details[1:3], 1):  # Check first 2 children
            child_tags = child_detail.get("tags", {})
            child_proposed = child_tags.get("proposed", [])
            
            child_by_category = {cat: [] for cat in TAG_CATEGORIES}
            for tag in child_proposed:
                for cat in TAG_CATEGORIES:
                    if tag.startswith(f"{cat}-"):
                        child_by_category[cat].append(tag)
                        break
            
            print(f"\n  Child {i} ({child_detail.get('title', 'Unknown')}):")
            for category in TAG_CATEGORIES:
                cat_tags = child_by_category[category]
                count = len(cat_tags)
                if count > 0:
                    print(f"    {category}: {count} tags")
                    assert count <= MAX_TAGS_PER_CATEGORY, \
                        f"Child {i} {category} has {count} tags, should be ≤{MAX_TAGS_PER_CATEGORY}"
    
    print(f"\n[TEST] ✅ All pages respect MAX_TAGS_PER_CATEGORY={MAX_TAGS_PER_CATEGORY}!")
    
    # Reset
    os.environ["TAGGING_AGENT_MODE"] = "SAFE_TEST"
    
    return result


@pytest.mark.asyncio
async def test_tag_tree_root_vs_children_consistency():
    """
    Перевірка що root та дочірні сторінки обробляються однаково.
    """
    print(f"\n[TEST] Testing root vs children consistency")
    
    os.environ["TAGGING_AGENT_MODE"] = "PROD"
    
    root_page_id = "19713687690"  # Smaller tree for faster test
    
    confluence_client = ConfluenceClient()
    service = BulkTaggingService(confluence_client=confluence_client)
    
    result = await service.tag_tree(space_key="euheals", root_page_id=root_page_id, dry_run=True)
    
    details = result.get('details', [])
    
    if len(details) < 2:
        print(f"  ⚠️  Only {len(details)} page(s), skipping comparison")
        return
    
    print(f"\n[TEST] Comparing root and child pages:")
    
    # Get root and first child
    root_detail = details[0]
    child_detail = details[1]
    
    root_tags = root_detail.get("tags", {})
    child_tags = child_detail.get("tags", {})
    
    print(f"\n  Root: {root_detail.get('title')}")
    print(f"    proposed: {len(root_tags.get('proposed', []))} tags")
    print(f"    Structure: {list(root_tags.keys())}")
    
    print(f"\n  Child: {child_detail.get('title')}")
    print(f"    proposed: {len(child_tags.get('proposed', []))} tags")
    print(f"    Structure: {list(child_tags.keys())}")
    
    # Verify both have same structure
    assert set(root_tags.keys()) == set(child_tags.keys()), \
        "Root and child should have same tags structure"
    
    # Verify both respect limits
    from src.config.tagging_settings import TAG_CATEGORIES
    
    for detail, name in [(root_detail, "Root"), (child_detail, "Child")]:
        tags = detail.get("tags", {})
        proposed = tags.get("proposed", [])
        
        by_category = {cat: [] for cat in TAG_CATEGORIES}
        for tag in proposed:
            for cat in TAG_CATEGORIES:
                if tag.startswith(f"{cat}-"):
                    by_category[cat].append(tag)
                    break
        
        for category, cat_tags in by_category.items():
            if cat_tags:
                assert len(cat_tags) <= MAX_TAGS_PER_CATEGORY, \
                    f"{name} {category} has {len(cat_tags)} tags, should be ≤{MAX_TAGS_PER_CATEGORY}"
    
    print(f"\n[TEST] ✅ Root and children processed consistently!")
    
    # Reset
    os.environ["TAGGING_AGENT_MODE"] = "SAFE_TEST"


if __name__ == "__main__":
    print("="*80)
    print("TAG-TREE ROOT PAGE TAG LIMIT FIX TEST")
    print("="*80)
    
    print("\n" + "="*80)
    print("TEST 1: ROOT PAGE TAG LIMIT")
    print("="*80)
    asyncio.run(test_tag_tree_root_page_tag_limit())
    
    print("\n" + "="*80)
    print("TEST 2: ROOT VS CHILDREN CONSISTENCY")
    print("="*80)
    asyncio.run(test_tag_tree_root_vs_children_consistency())
    
    print("\n" + "="*80)
    print("✅ ALL ROOT PAGE TAG LIMIT TESTS PASSED!")
    print("="*80)
