"""
Comprehensive test for режимна матриця in bulk tagging
"""
import pytest
import asyncio
from src.services.bulk_tagging_service import BulkTaggingService
from src.core.logging.logging_config import configure_logging
import os

configure_logging()


@pytest.mark.asyncio
async def test_режимна_матриця_test_mode():
    """
    TEST MODE:
    - dry_run=None  → dry-run (status="dry_run")
    - dry_run=true  → dry-run (status="dry_run")
    - dry_run=false → forbidden (status="forbidden")
    """
    os.environ["TAGGING_AGENT_MODE"] = "TEST"
    
    service = BulkTaggingService()
    page_ids = ["19713687690"]
    
    print(f"\n[TEST] TEST MODE:")
    print(f"  Agent mode: {service.agent.mode}")
    
    # 1. dry_run=None → dry-run
    print(f"\n  Test 1: dry_run=None")
    result1 = await service.tag_pages(page_ids, space_key="euheals", dry_run=None)
    assert result1["dry_run"] == True, "TEST mode with dry_run=None should be dry-run"
    assert result1["details"][0]["status"] == "dry_run"
    print(f"    ✅ dry_run=None → status={result1['details'][0]['status']}, dry_run={result1['dry_run']}")
    
    # 2. dry_run=True → dry-run
    print(f"  Test 2: dry_run=True")
    result2 = await service.tag_pages(page_ids, space_key="euheals", dry_run=True)
    assert result2["dry_run"] == True
    assert result2["details"][0]["status"] == "dry_run"
    print(f"    ✅ dry_run=True → status={result2['details'][0]['status']}, dry_run={result2['dry_run']}")
    
    # 3. dry_run=False → forbidden
    print(f"  Test 3: dry_run=False")
    result3 = await service.tag_pages(page_ids, space_key="euheals", dry_run=False)
    assert result3["dry_run"] == False
    assert result3["details"][0]["status"] == "forbidden", "TEST mode with dry_run=False should be forbidden"
    assert result3["details"][0]["tags"] is None, "Forbidden should have tags=null"
    print(f"    ✅ dry_run=False → status={result3['details'][0]['status']}, tags={result3['details'][0]['tags']}")
    
    print(f"\n[TEST] ✅ TEST MODE matrix passed!")
    
    # Reset
    os.environ["TAGGING_AGENT_MODE"] = "TEST"


@pytest.mark.asyncio
async def test_режимна_матриця_safe_test_mode():
    """
    SAFE_TEST MODE:
    - Whitelist + dry_run=None  → updated
    - Whitelist + dry_run=false → updated
    - Non-whitelist + dry_run=None  → forbidden
    - Non-whitelist + dry_run=false → forbidden
    - dry_run=true → dry-run (для всіх сторінок)
    """
    os.environ["TAGGING_AGENT_MODE"] = "SAFE_TEST"
    
    service = BulkTaggingService()
    
    whitelist_page = "19713687690"  # In TAGGING_AGENT_TEST_PAGE
    non_whitelist_page = "19700089019"  # Not in TAGGING_AGENT_TEST_PAGE
    
    print(f"\n[TEST] SAFE_TEST MODE:")
    print(f"  Agent mode: {service.agent.mode}")
    print(f"  Whitelist: {service.agent.allowed_test_pages}")
    
    # 1. Whitelist + dry_run=None → updated
    print(f"\n  Test 1: Whitelist + dry_run=None")
    result1 = await service.tag_pages([whitelist_page], space_key="euheals", dry_run=None)
    assert result1["dry_run"] == False, "SAFE_TEST with dry_run=None should NOT be dry-run"
    assert result1["details"][0]["status"] == "updated", "Whitelist page should be updated"
    print(f"    ✅ Whitelist + dry_run=None → status={result1['details'][0]['status']}")
    
    # 2. Whitelist + dry_run=False → updated
    print(f"  Test 2: Whitelist + dry_run=False")
    result2 = await service.tag_pages([whitelist_page], space_key="euheals", dry_run=False)
    assert result2["dry_run"] == False
    assert result2["details"][0]["status"] == "updated"
    print(f"    ✅ Whitelist + dry_run=False → status={result2['details'][0]['status']}")
    
    # 3. Non-whitelist + dry_run=None → forbidden
    print(f"  Test 3: Non-whitelist + dry_run=None")
    result3 = await service.tag_pages([non_whitelist_page], space_key="euheals", dry_run=None)
    assert result3["dry_run"] == False
    assert result3["details"][0]["status"] == "forbidden", "Non-whitelist should be forbidden"
    assert result3["details"][0]["tags"] is None
    print(f"    ✅ Non-whitelist + dry_run=None → status={result3['details'][0]['status']}, tags=null")
    
    # 4. Non-whitelist + dry_run=False → forbidden
    print(f"  Test 4: Non-whitelist + dry_run=False")
    result4 = await service.tag_pages([non_whitelist_page], space_key="euheals", dry_run=False)
    assert result4["details"][0]["status"] == "forbidden"
    print(f"    ✅ Non-whitelist + dry_run=False → status={result4['details'][0]['status']}")
    
    # 5. dry_run=True → dry-run (всі сторінки)
    print(f"  Test 5: Both pages + dry_run=True")
    result5 = await service.tag_pages([whitelist_page, non_whitelist_page], space_key="euheals", dry_run=True)
    assert result5["dry_run"] == True
    assert all(d["status"] == "dry_run" for d in result5["details"])
    print(f"    ✅ dry_run=True → all pages dry-run")
    
    print(f"\n[TEST] ✅ SAFE_TEST MODE matrix passed!")
    
    # Reset
    os.environ["TAGGING_AGENT_MODE"] = "TEST"


@pytest.mark.asyncio
async def test_режимна_матриця_prod_mode():
    """
    PROD MODE:
    - dry_run=None  → updated (всі сторінки)
    - dry_run=false → updated (всі сторінки)
    - dry_run=true  → dry-run (всі сторінки)
    """
    os.environ["TAGGING_AGENT_MODE"] = "PROD"
    
    service = BulkTaggingService()
    
    page_ids = ["19713687690", "19700089019"]
    
    print(f"\n[TEST] PROD MODE:")
    print(f"  Agent mode: {service.agent.mode}")
    
    # 1. dry_run=None → updated (всі сторінки)
    print(f"\n  Test 1: All pages + dry_run=None")
    result1 = await service.tag_pages(page_ids, space_key="euheals", dry_run=None)
    assert result1["dry_run"] == False, "PROD mode with dry_run=None should NOT be dry-run"
    assert all(d["status"] == "updated" for d in result1["details"]), "All pages should be updated in PROD"
    print(f"    ✅ dry_run=None → all updated ({len(result1['details'])} pages)")
    
    # 2. dry_run=False → updated (всі сторінки)
    print(f"  Test 2: All pages + dry_run=False")
    result2 = await service.tag_pages(page_ids, space_key="euheals", dry_run=False)
    assert result2["dry_run"] == False
    assert all(d["status"] == "updated" for d in result2["details"])
    print(f"    ✅ dry_run=False → all updated")
    
    # 3. dry_run=True → dry-run (всі сторінки)
    print(f"  Test 3: All pages + dry_run=True")
    result3 = await service.tag_pages(page_ids, space_key="euheals", dry_run=True)
    assert result3["dry_run"] == True
    assert all(d["status"] == "dry_run" for d in result3["details"])
    print(f"    ✅ dry_run=True → all dry-run")
    
    print(f"\n[TEST] ✅ PROD MODE matrix passed!")
    
    # Reset
    os.environ["TAGGING_AGENT_MODE"] = "TEST"


@pytest.mark.asyncio
async def test_tags_structure_forbidden():
    """
    Verify that forbidden pages have tags=null
    """
    os.environ["TAGGING_AGENT_MODE"] = "TEST"
    
    service = BulkTaggingService()
    page_ids = ["19713687690"]
    
    print(f"\n[TEST] Tags structure for forbidden:")
    
    # In TEST mode with dry_run=False → forbidden
    result = await service.tag_pages(page_ids, space_key="euheals", dry_run=False)
    
    detail = result["details"][0]
    assert detail["status"] == "forbidden"
    assert detail["tags"] is None, "Forbidden must have tags=null"
    assert "message" in detail, "Forbidden must have message"
    
    print(f"  Status: {detail['status']}")
    print(f"  Tags: {detail['tags']}")
    print(f"  Message: {detail.get('message', 'N/A')[:50]}...")
    print(f"\n[TEST] ✅ Forbidden tags structure correct!")
    
    # Reset
    os.environ["TAGGING_AGENT_MODE"] = "TEST"


if __name__ == "__main__":
    print("="*80)
    print("РЕЖИМНА МАТРИЦЯ COMPREHENSIVE TEST")
    print("="*80)
    
    print("\n" + "="*80)
    print("TEST 1: TEST MODE MATRIX")
    print("="*80)
    asyncio.run(test_режимна_матриця_test_mode())
    
    print("\n" + "="*80)
    print("TEST 2: SAFE_TEST MODE MATRIX")
    print("="*80)
    asyncio.run(test_режимна_матриця_safe_test_mode())
    
    print("\n" + "="*80)
    print("TEST 3: PROD MODE MATRIX")
    print("="*80)
    asyncio.run(test_режимна_матриця_prod_mode())
    
    print("\n" + "="*80)
    print("TEST 4: FORBIDDEN TAGS STRUCTURE")
    print("="*80)
    asyncio.run(test_tags_structure_forbidden())
    
    print("="*80)
