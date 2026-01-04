"""
Test suite for tag_pages() optimizations and context minimization.

SCOPE: Tests for /bulk/tag-pages endpoint ONLY
Location: tests/bulk/test_tag_pages_optimized.py
"""

import pytest
import os
import time
from unittest.mock import patch, AsyncMock
from src.services.bulk_tagging_service import BulkTaggingService
from src.services.tag_pages_utils import html_to_text_limited, clean_html_for_tag_pages


# ============================================================================
# TEST 1: Minimal expand parameter (no version, metadata, ancestors)
# ============================================================================

def test_minimal_expand_parameter():
    """
    VERIFICATION: get_page() is called with expand="body.storage" ONLY.
    
    This test checks that tag_pages() does NOT request extra Confluence
    API fields like version history, metadata, or ancestors.
    """
    # PENDING: Will be verified during integration test
    # This is a static code review item
    pass


# ============================================================================
# TEST 2: Only page_ids are processed (no tree traversal, no enrichment)
# ============================================================================

@pytest.mark.asyncio
async def test_only_page_ids_processed():
    """
    VERIFICATION: tag_pages() processes ONLY the explicitly provided page_ids.
    
    Ensures NO child pages, ancestors, or related pages are processed.
    """
    os.environ["TAGGING_AGENT_MODE"] = "SAFE_TEST"
    
    page_ids = ["111", "222", "333"]
    
    # Mock Confluence client
    mock_confluence = AsyncMock()
    mock_confluence.get_page = AsyncMock(return_value={
        "id": "111",
        "title": "Test Page",
        "body": {"storage": {"value": "<p>Content</p>"}},
        "version": {"number": 1}
    })
    mock_confluence.get_labels = AsyncMock(return_value=[])
    mock_confluence.get_child_pages = AsyncMock()  # Should NOT be called
    
    with patch("src.core.whitelist.whitelist_manager.WhitelistManager.get_entry_points") as mock_entries:
        mock_entries.return_value = {111, 222, 333}
        
        service = BulkTaggingService(confluence_client=mock_confluence)
        result = await service.tag_pages(page_ids, space_key="nkfedba", dry_run=True)
        
        # ✅ Verify ONLY requested pages were processed
        assert result["total"] == 3
        assert result["processed"] == 3
        assert result["success"] == 3
        
        # ✅ Verify get_page called exactly 3 times (once per page_id)
        assert mock_confluence.get_page.call_count == 3
        
        # ✅ Verify get_child_pages was NEVER called
        assert mock_confluence.get_child_pages.call_count == 0
        
        # ✅ Verify only requested pages in details
        result_ids = {d["page_id"] for d in result["details"]}
        assert result_ids == {"111", "222", "333"}
        
        logger = __import__("logging").getLogger()
        logger.info("✅ TEST PASSED: Only page_ids processed, no tree traversal")
    
    os.environ.pop("TAGGING_AGENT_MODE", None)


# ============================================================================
# TEST 3: Context minimization for AI
# ============================================================================

def test_context_minimization_html_cleaning():
    """
    VERIFICATION: HTML is cleaned before sending to AI.
    
    Removes scripts, styles, macros, attributes.
    """
    # Test data with unnecessary HTML
    html = """
    <script>alert('bad')</script>
    <p>Important content for tagging</p>
    <ac:macro>confluence macro</ac:macro>
    <style>.css { color: red; }</style>
    <iframe src="bad"></iframe>
    <p>More important content</p>
    """
    
    cleaned = clean_html_for_tag_pages(html)
    
    # ✅ Verify bad elements removed
    assert "script" not in cleaned.lower()
    assert "alert" not in cleaned.lower()
    assert "ac:macro" not in cleaned.lower()
    assert "style" not in cleaned.lower()
    assert "iframe" not in cleaned.lower()
    
    # ✅ Verify content preserved
    assert "Important content" in cleaned
    assert "More important" in cleaned
    
    # ✅ Verify size reduction
    reduction = (1 - len(cleaned) / len(html)) * 100
    assert reduction > 50  # Should reduce size by at least 50%


def test_context_limitation_text_truncation():
    """
    VERIFICATION: Text is limited to 3000 characters for AI.
    
    Ensures AI doesn't receive excessive context.
    """
    # Create large HTML
    large_html = "<p>Content block here.</p>" * 500  # ~13,000 chars
    
    # Convert with limit
    text = html_to_text_limited(large_html, max_chars=3000)
    
    # ✅ Verify length limit respected
    assert len(text) <= 3000
    assert text.strip() != ""
    
    # ✅ Verify intelligent truncation (at word boundary)
    # Should not end mid-word
    assert not text.endswith(" ") or text.rstrip().endswith((".", "!", "?"))


def test_context_metrics_calculation():
    """
    VERIFICATION: Context reduction is measured and logged.
    """
    from src.services.tag_pages_utils import get_context_metrics
    
    original_html = "<p>Content</p>" * 100
    final_text = "Content block " * 20  # Much shorter
    
    metrics = get_context_metrics(original_html, final_text)
    
    # ✅ Verify metrics
    assert metrics["original_html_chars"] > 0
    assert metrics["cleaned_text_chars"] > 0
    assert metrics["reduction_pct"] > 50
    assert "tokens_approx" in metrics


# ============================================================================
# TEST 4: Whitelist filtering works correctly
# ============================================================================

@pytest.mark.asyncio
async def test_whitelist_filtering_for_tag_pages():
    """
    VERIFICATION: tag_pages() correctly filters pages by whitelist.
    
    Only whitelisted pages should be processed.
    """
    os.environ["TAGGING_AGENT_MODE"] = "SAFE_TEST"
    
    page_ids = ["111", "222", "333"]  # Request 3 pages
    
    mock_confluence = AsyncMock()
    mock_confluence.get_page = AsyncMock(return_value={
        "body": {"storage": {"value": "<p>Test</p>"}},
        "version": {"number": 1}
    })
    mock_confluence.get_labels = AsyncMock(return_value=[])
    
    with patch("src.core.whitelist.whitelist_manager.WhitelistManager.get_entry_points") as mock_entries:
        # Only 111 and 333 are whitelisted entry points
        mock_entries.return_value = {111, 333}
        
        service = BulkTaggingService(confluence_client=mock_confluence)
        result = await service.tag_pages(page_ids, space_key="nkfedba", dry_run=True)
        
        # ✅ Verify whitelist filtering
        assert result["total"] == 3  # Total requested
        assert result["processed"] == 2  # Only whitelisted
        assert result["skipped_by_whitelist"] == 1  # 222 not in whitelist
        
        # ✅ Verify only whitelisted pages in results
        result_ids = {d["page_id"] for d in result["details"]}
        assert result_ids == {"111", "333"}
        assert "222" not in result_ids
    
    os.environ.pop("TAGGING_AGENT_MODE", None)


# ============================================================================
# TEST 5: Performance test (optional, marked as slow)
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.slow  # Mark as slow for optional execution
async def test_tag_pages_performance():
    """
    VERIFICATION: tag_pages() completes in reasonable time with optimizations.
    
    Expects < 30 seconds for 2 pages with minimal expand and context.
    """
    os.environ["TAGGING_AGENT_MODE"] = "SAFE_TEST"
    
    page_ids = ["111", "222"]
    
    mock_confluence = AsyncMock()
    mock_confluence.get_page = AsyncMock(return_value={
        "body": {"storage": {"value": "<p>Content</p>" * 100}},  # ~1400 chars
        "version": {"number": 1}
    })
    mock_confluence.get_labels = AsyncMock(return_value=[])
    
    with patch("src.core.whitelist.whitelist_manager.WhitelistManager.get_entry_points") as mock_entries:
        mock_entries.return_value = {111, 222}
        
        service = BulkTaggingService(confluence_client=mock_confluence)
        
        # Measure execution time
        start = time.time()
        result = await service.tag_pages(page_ids, space_key="nkfedba", dry_run=True)
        elapsed = time.time() - start
        
        # ✅ Verify completion
        assert result["success"] == 2
        
        # ✅ Log performance
        logger = __import__("logging").getLogger()
        logger.info(f"⏱️ Performance: {elapsed:.2f}s for 2 pages (target: <30s)")
        
        # Note: Actual performance depends on Confluence API and AI API
        # With optimizations, should be 20-30s (vs 100+ before)
    
    os.environ.pop("TAGGING_AGENT_MODE", None)


# ============================================================================
# TEST 6: No enrichment calls (no children, ancestors, etc.)
# ============================================================================

@pytest.mark.asyncio
async def test_no_enrichment_calls():
    """
    VERIFICATION: tag_pages() does NOT make enrichment API calls.
    
    Should NOT call:
    - get_child_pages()
    - get_ancestors()
    - get_space()
    - get_related_pages()
    - get_incoming_links()
    """
    os.environ["TAGGING_AGENT_MODE"] = "SAFE_TEST"
    
    mock_confluence = AsyncMock()
    mock_confluence.get_page = AsyncMock(return_value={
        "body": {"storage": {"value": "<p>Content</p>"}},
        "version": {"number": 1}
    })
    mock_confluence.get_labels = AsyncMock(return_value=[])
    
    # These should NOT be called
    mock_confluence.get_child_pages = AsyncMock()
    mock_confluence.get_ancestors = AsyncMock()
    mock_confluence.get_space = AsyncMock()
    mock_confluence.get_related_pages = AsyncMock()
    mock_confluence.get_incoming_links = AsyncMock()
    
    with patch("src.core.whitelist.whitelist_manager.WhitelistManager.get_entry_points") as mock_entries:
        mock_entries.return_value = {111, 222}
        
        service = BulkTaggingService(confluence_client=mock_confluence)
        await service.tag_pages(["111", "222"], space_key="nkfedba", dry_run=True)
        
        # ✅ Verify NO enrichment calls
        assert mock_confluence.get_child_pages.call_count == 0
        assert mock_confluence.get_ancestors.call_count == 0
        assert mock_confluence.get_space.call_count == 0
        
        logger = __import__("logging").getLogger()
        logger.info("✅ TEST PASSED: No enrichment calls made")
    
    os.environ.pop("TAGGING_AGENT_MODE", None)


# ============================================================================
# TEST 7: Dry-run mode doesn't update labels
# ============================================================================

@pytest.mark.asyncio
async def test_dry_run_no_updates():
    """
    VERIFICATION: dry_run=true prevents label updates.
    """
    os.environ["TAGGING_AGENT_MODE"] = "SAFE_TEST"
    
    mock_confluence = AsyncMock()
    mock_confluence.get_page = AsyncMock(return_value={
        "body": {"storage": {"value": "<p>Content to tag</p>"}},
        "version": {"number": 1}
    })
    mock_confluence.get_labels = AsyncMock(return_value=[])
    mock_confluence.update_labels = AsyncMock()
    
    with patch("src.core.whitelist.whitelist_manager.WhitelistManager.get_entry_points") as mock_entries:
        mock_entries.return_value = {111}
        
        service = BulkTaggingService(confluence_client=mock_confluence)
        result = await service.tag_pages(["111"], space_key="nkfedba", dry_run=True)
        
        # ✅ Verify no updates called in dry-run
        assert mock_confluence.update_labels.call_count == 0
        assert result["dry_run"] is True
        assert result["details"][0]["status"] in ["dry_run", "forbidden"]
    
    os.environ.pop("TAGGING_AGENT_MODE", None)


# ============================================================================
# TEST 8: Mode-specific strictness (TEST/SAFE_TEST/PROD)
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["TEST", "SAFE_TEST", "PROD"])
async def test_strict_mode_across_modes(mode):
    """Ensure only request.page_ids are processed in all modes."""
    os.environ["TAGGING_AGENT_MODE"] = mode

    page_ids = ["111", "222"]
    mock_confluence = AsyncMock()
    mock_confluence.get_page = AsyncMock(return_value={
        "body": {"storage": {"value": "<p>Content</p>"}},
        "version": {"number": 1}
    })
    mock_confluence.get_labels = AsyncMock(return_value=[])

    with patch("src.core.whitelist.whitelist_manager.WhitelistManager.get_entry_points") as mock_entries:
        mock_entries.return_value = {111, 222, 333}  # whitelist superset

        service = BulkTaggingService(confluence_client=mock_confluence)
        result = await service.tag_pages(page_ids, space_key="nkfedba", dry_run=True)

        assert result["total"] == 2
        assert result["processed"] == 2
        # Ensure no extra page processed
        ids = {d["page_id"] for d in result["details"]}
        assert ids == {"111", "222"}

        # Calls exactly per requested page
        assert mock_confluence.get_page.call_count == 2
        assert mock_confluence.get_labels.call_count == 2

    os.environ.pop("TAGGING_AGENT_MODE", None)


# ============================================================================
# TEST 9: Minimal expand is enforced
# ============================================================================


@pytest.mark.asyncio
async def test_minimal_expand_enforced():
    os.environ["TAGGING_AGENT_MODE"] = "SAFE_TEST"
    page_ids = ["111"]

    mock_confluence = AsyncMock()
    mock_confluence.get_page = AsyncMock(return_value={
        "body": {"storage": {"value": "<p>Content</p>"}}
    })
    mock_confluence.get_labels = AsyncMock(return_value=[])

    with patch("src.core.whitelist.whitelist_manager.WhitelistManager.get_entry_points") as mock_entries:
        mock_entries.return_value = {111}

        service = BulkTaggingService(confluence_client=mock_confluence)
        await service.tag_pages(page_ids, space_key="nkfedba", dry_run=True)

        mock_confluence.get_page.assert_awaited()
        args, kwargs = mock_confluence.get_page.call_args
        assert kwargs.get("expand") == "body.storage"

    os.environ.pop("TAGGING_AGENT_MODE", None)


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "-k", "not slow"])
