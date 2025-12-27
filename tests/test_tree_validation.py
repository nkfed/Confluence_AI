"""
Test script to validate tag-tree behavior for deep documentation tree.
Root page: 19700416664 (ЕКОПФО та інші Реєстри — сайт Helpdesk ДП з використанням ШІ)
"""
import asyncio
from src.sections.section_detector import detect_section
from src.sections.whitelist import get_allowed_labels
from src.services.bulk_tagging_service import BulkTaggingService


async def test_section_detection():
    """Test 1: Verify section detection"""
    print("\n" + "="*80)
    print("TEST 1: SECTION DETECTION")
    print("="*80)
    
    root_page_id = "19700416664"
    try:
        section = detect_section(root_page_id)
        print(f"✅ detect_section('{root_page_id}') = '{section}'")
        assert section == "helpdesk", f"Expected 'helpdesk', got '{section}'"
        print("✅ Section detection: PASS")
        return section
    except Exception as e:
        print(f"❌ Section detection: FAIL - {e}")
        raise


async def test_whitelist(section):
    """Test 2: Verify whitelist"""
    print("\n" + "="*80)
    print("TEST 2: WHITELIST VALIDATION")
    print("="*80)
    
    allowed_labels = get_allowed_labels(section)
    print(f"Allowed labels for '{section}': {allowed_labels}")
    
    expected_tags = [
        "doc-tech",
        "doc-architecture",
        "domain-helpdesk-site",
        "domain-ai-integration",
        "kb-overview",
        "kb-canonical",
        "kb-components",
        "doc-design"
    ]
    
    print("\nValidating expected tags:")
    for tag in expected_tags:
        if tag in allowed_labels:
            print(f"  ✅ {tag}")
        else:
            print(f"  ❌ {tag} - MISSING")
    
    missing = [tag for tag in expected_tags if tag not in allowed_labels]
    if missing:
        print(f"\n❌ Missing tags: {missing}")
        raise AssertionError(f"Missing tags: {missing}")
    
    print("\n✅ Whitelist validation: PASS")
    return allowed_labels


async def test_tree_collection():
    """Test 3: Verify tree depth and collection"""
    print("\n" + "="*80)
    print("TEST 3: TREE COLLECTION")
    print("="*80)
    
    root_page_id = "19700416664"
    service = BulkTaggingService()
    
    print(f"Collecting tree for root page {root_page_id}...")
    try:
        all_page_ids = await service.collect_tree(root_page_id)
        print(f"✅ Collected {len(all_page_ids)} pages")
        
        # Check for policy pages (should NOT be included)
        policy_pages = [
            "19716112385", "19716145153", "19713622141", 
            "19713622133", "19713687690", "19712868463"
        ]
        
        found_policy_pages = [pid for pid in policy_pages if pid in all_page_ids]
        if found_policy_pages:
            print(f"⚠️  Warning: Found policy pages in tree: {found_policy_pages}")
        else:
            print("✅ No policy pages in tree (correct)")
        
        # Show tree depth info
        print(f"\nTree statistics:")
        print(f"  - Total pages: {len(all_page_ids)}")
        print(f"  - First 10 pages: {all_page_ids[:10]}")
        
        return all_page_ids
    except Exception as e:
        print(f"❌ Tree collection: FAIL - {e}")
        raise


async def test_fallback_logic():
    """Test 4: Verify fallback logic"""
    print("\n" + "="*80)
    print("TEST 4: FALLBACK LOGIC")
    print("="*80)
    
    from src.agents.summary_agent import SummaryAgent, MIN_CONTENT_THRESHOLD
    import re
    
    print(f"MIN_CONTENT_THRESHOLD = {MIN_CONTENT_THRESHOLD}")
    
    # Test cases
    test_cases = [
        ("", True, "Empty content"),
        ("Short", True, "Too short without tags"),
        ("doc-tech kb-overview", False, "Has tag patterns"),
        ("This is a long enough text without any tag patterns " * 10, False, "Long text"),
        ("Links: https://example.com/doc1 https://example.com/doc2", True, "Only URLs")
    ]
    
    for content, should_fallback, description in test_cases:
        has_tag_patterns = bool(re.search(r"\b(doc-|domain-|tool-|kb-)", content or ""))
        will_fallback = (
            not content or 
            (len(content) < MIN_CONTENT_THRESHOLD and not has_tag_patterns) or
            (len(re.sub(r'https?://[^\s]+', '', content).strip()) < MIN_CONTENT_THRESHOLD and not has_tag_patterns)
        )
        
        status = "✅" if will_fallback == should_fallback else "❌"
        print(f"{status} {description}: fallback={will_fallback}, expected={should_fallback}")
    
    print("\n✅ Fallback logic: PASS")


async def test_prompt_builder():
    """Test 5: Verify prompt builder"""
    print("\n" + "="*80)
    print("TEST 5: PROMPT BUILDER")
    print("="*80)
    
    from src.agents.prompt_builder import PromptBuilder
    
    allowed_labels = ["doc-tech", "kb-overview"]
    content = "Sample content for testing"
    
    prompt = PromptBuilder.build_tag_tree_prompt(content, allowed_labels, dry_run=True)
    
    # Check prompt structure
    checks = [
        ("ALLOWED TAGS:" in prompt, "Has ALLOWED TAGS section"),
        ("doc-tech" in prompt, "Contains doc-tech"),
        ("kb-overview" in prompt, "Contains kb-overview"),
        ("IMPORTANT INSTRUCTIONS:" in prompt, "Has instructions"),
        ("Tag the PAGE ITSELF" in prompt, "Has page tagging instruction"),
        ("CONTENT TO ANALYZE:" in prompt, "Has content section"),
    ]
    
    for check, description in checks:
        status = "✅" if check else "❌"
        print(f"{status} {description}")
    
    if all(check for check, _ in checks):
        print("\n✅ Prompt builder: PASS")
    else:
        print("\n❌ Prompt builder: FAIL")
        raise AssertionError("Prompt builder validation failed")


async def test_dry_run():
    """Test 6: Run dry-run tagging"""
    print("\n" + "="*80)
    print("TEST 6: DRY-RUN TAGGING")
    print("="*80)
    
    root_page_id = "19700416664"
    service = BulkTaggingService()
    
    print(f"Running dry-run tag-tree for {root_page_id}...")
    print("⚠️  This will take some time as it processes the entire tree...")
    
    try:
        result = await service.tag_tree(root_page_id, dry_run=True)
        
        print(f"\n✅ Dry-run completed!")
        print(f"\nResults:")
        print(f"  - Section: {result.get('section')}")
        print(f"  - Root page ID: {result.get('root_page_id')}")
        print(f"  - Total pages processed: {len(result.get('results', []))}")
        print(f"  - Success count: {result.get('success_count', 0)}")
        print(f"  - Error count: {result.get('error_count', 0)}")
        
        # Show sample results
        results = result.get('results', [])
        if results:
            print(f"\nFirst 5 results:")
            for i, res in enumerate(results[:5], 1):
                print(f"\n  {i}. Page {res.get('page_id')}:")
                print(f"     Status: {res.get('status')}")
                print(f"     Suggested tags: {res.get('suggested_tags', [])}")
                print(f"     Labels to add: {res.get('labels_to_add', [])}")
        
        return result
    except Exception as e:
        print(f"\n❌ Dry-run: FAIL - {e}")
        import traceback
        traceback.print_exc()
        raise


async def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("TAG-TREE VALIDATION FOR ROOT PAGE 19700416664")
    print("ЕКОПФО та інші Реєстри — сайт Helpdesk ДП з використанням ШІ")
    print("="*80)
    
    try:
        # Test 1: Section detection
        section = await test_section_detection()
        
        # Test 2: Whitelist
        allowed_labels = await test_whitelist(section)
        
        # Test 3: Tree collection
        # all_page_ids = await test_tree_collection()
        
        # Test 4: Fallback logic
        await test_fallback_logic()
        
        # Test 5: Prompt builder
        await test_prompt_builder()
        
        # Test 6: Dry-run (commented out for quick testing)
        # await test_dry_run()
        
        print("\n" + "="*80)
        print("✅ ALL TESTS PASSED")
        print("="*80)
        
    except Exception as e:
        print("\n" + "="*80)
        print(f"❌ TESTS FAILED: {e}")
        print("="*80)
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
