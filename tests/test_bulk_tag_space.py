"""
Комплексні тести для BulkTagOrchestrator та ендпоінту POST /bulk/tag-space/{space_key}.

Перевіряє:
- Режимну логіку (TEST/SAFE_TEST/PROD)
- Dry-run режим
- Фільтрацію сторінок
- Whitelist у SAFE_TEST режимі
- Обмеження тегів (limit_tags_per_category)
- Обробку помилок AI
- Обробку помилок Confluence
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.core.bulk_tag_orchestrator import BulkTagOrchestrator
from settings import AgentMode


@pytest.fixture
def mock_confluence_client():
    """Mock Confluence client."""
    client = MagicMock()
    client.get_pages_in_space = AsyncMock(return_value=[
        {
            "id": "123",
            "title": "Test Page 1",
            "status": "current",
            "type": "page",
            "body": {"storage": {"value": "<p>Content for page 1</p>" * 100}}
        },
        {
            "id": "456",
            "title": "Test Page 2",
            "status": "current",
            "type": "page",
            "body": {"storage": {"value": "<p>Content for page 2</p>" * 100}}
        }
    ])
    client.get_labels = AsyncMock(return_value=["existing-tag"])
    client.add_labels = AsyncMock(return_value={"added": [], "errors": []})
    return client


@pytest.fixture
def mock_tagging_agent():
    """Mock TaggingAgent."""
    agent = MagicMock()
    agent.suggest_tags = AsyncMock(return_value={
        "doc": ["doc-tech", "doc-business"],
        "domain": ["domain-helpdesk-site"],
        "kb": [],
        "tool": []
    })
    return agent


@pytest.mark.asyncio
@patch.dict("os.environ", {"AGENT_MODE": "TEST"})
async def test_bulk_tag_space_test_mode_always_dry_run(
    mock_confluence_client,
    mock_tagging_agent
):
    """
    Тест: TEST режим завжди використовує dry_run=True.
    """
    orchestrator = BulkTagOrchestrator(
        confluence_client=mock_confluence_client,
        tagging_agent=mock_tagging_agent
    )
    
    # Спробувати з dry_run=False (має бути проігноровано)
    result = await orchestrator.tag_space(
        space_key="TEST",
        dry_run_override=False
    )
    
    # Verify TEST mode enforces dry_run
    assert result["dry_run"] is True
    assert result["mode"] == AgentMode.TEST
    
    # Verify no actual writes
    mock_confluence_client.add_labels.assert_not_called()


@pytest.mark.asyncio
@patch.dict("os.environ", {"AGENT_MODE": "PROD"})
async def test_bulk_tag_space_prod_mode_respects_dry_run(
    mock_confluence_client,
    mock_tagging_agent
):
    """
    Тест: PROD режим дозволяє контролювати dry_run.
    """
    with patch("src.core.bulk_tag_orchestrator.AgentModeResolver") as mock_resolver:
        mock_resolver.resolve_mode.return_value = AgentMode.PROD
        mock_resolver.resolve_whitelist.return_value = []
        mock_resolver.can_modify_confluence.return_value = True
        
        orchestrator = BulkTagOrchestrator(
            confluence_client=mock_confluence_client,
            tagging_agent=mock_tagging_agent
        )
        
        # Test dry_run=False
        result = await orchestrator.tag_space(
            space_key="TEST",
            dry_run_override=False
        )
        
        # Verify PROD mode allows writes
        assert result["dry_run"] is False
        assert result["mode"] == AgentMode.PROD
        
        # Verify actual writes attempted
        assert mock_confluence_client.add_labels.call_count > 0


@pytest.mark.asyncio
@patch.dict("os.environ", {"AGENT_MODE": "SAFE_TEST", "TAGGING_AGENT_TEST_PAGE": "123"})
async def test_bulk_tag_space_safe_test_whitelist(
    mock_confluence_client,
    mock_tagging_agent
):
    """
    Тест: SAFE_TEST режим застосовує whitelist.
    """
    with patch("src.core.bulk_tag_orchestrator.AgentModeResolver") as mock_resolver:
        mock_resolver.resolve_mode.return_value = AgentMode.SAFE_TEST
        mock_resolver.resolve_whitelist.return_value = ["123"]  # Only page 123
        mock_resolver.can_modify_confluence = lambda mode, page_id, whitelist: page_id in whitelist
        
        orchestrator = BulkTagOrchestrator(
            confluence_client=mock_confluence_client,
            tagging_agent=mock_tagging_agent
        )
        
        result = await orchestrator.tag_space(
            space_key="TEST",
            dry_run_override=False
        )
        
        # Verify whitelist filtering
        assert result["skipped_count"] == 1  # Page 456 skipped
        assert result["processed"] == 1      # Only page 123 processed


@pytest.mark.asyncio
async def test_bulk_tag_space_filters_archived_pages(
    mock_confluence_client,
    mock_tagging_agent
):
    """
    Тест: фільтрація архівованих сторінок.
    """
    # Add archived page
    mock_confluence_client.get_pages_in_space = AsyncMock(return_value=[
        {
            "id": "123",
            "title": "Current Page",
            "status": "current",
            "type": "page",
            "body": {"storage": {"value": "<p>Content</p>" * 100}}
        },
        {
            "id": "456",
            "title": "Archived Page",
            "status": "archived",
            "type": "page",
            "body": {"storage": {"value": "<p>Content</p>" * 100}}
        }
    ])
    
    with patch("src.core.bulk_tag_orchestrator.AgentModeResolver") as mock_resolver:
        mock_resolver.resolve_mode.return_value = AgentMode.PROD
        mock_resolver.resolve_whitelist.return_value = []
        mock_resolver.can_modify_confluence.return_value = True
        
        orchestrator = BulkTagOrchestrator(
            confluence_client=mock_confluence_client,
            tagging_agent=mock_tagging_agent
        )
        
        result = await orchestrator.tag_space(
            space_key="TEST",
            dry_run_override=False,
            exclude_archived=True
        )
        
        # Verify archived page was skipped
        assert result["skipped_count"] == 1
        assert result["skipped_pages"][0]["reason"] == "Page is archived"


@pytest.mark.asyncio
async def test_bulk_tag_space_filters_index_pages(
    mock_confluence_client,
    mock_tagging_agent
):
    """
    Тест: фільтрація індексних сторінок.
    """
    mock_confluence_client.get_pages_in_space = AsyncMock(return_value=[
        {
            "id": "123",
            "title": "Regular Page",
            "status": "current",
            "type": "page",
            "body": {"storage": {"value": "<p>Content</p>" * 100}}
        },
        {
            "id": "456",
            "title": "Index",
            "status": "current",
            "type": "page",
            "body": {"storage": {"value": "<p>Content</p>" * 100}}
        }
    ])
    
    with patch("src.core.bulk_tag_orchestrator.AgentModeResolver") as mock_resolver:
        mock_resolver.resolve_mode.return_value = AgentMode.PROD
        mock_resolver.resolve_whitelist.return_value = []
        mock_resolver.can_modify_confluence.return_value = True
        
        orchestrator = BulkTagOrchestrator(
            confluence_client=mock_confluence_client,
            tagging_agent=mock_tagging_agent
        )
        
        result = await orchestrator.tag_space(
            space_key="TEST",
            dry_run_override=False,
            exclude_index_pages=True
        )
        
        # Verify index page was skipped
        assert result["skipped_count"] == 1
        assert "index" in result["skipped_pages"][0]["reason"].lower()


@pytest.mark.asyncio
async def test_bulk_tag_space_filters_empty_pages(
    mock_confluence_client,
    mock_tagging_agent
):
    """
    Тест: фільтрація порожніх сторінок.
    """
    mock_confluence_client.get_pages_in_space = AsyncMock(return_value=[
        {
            "id": "123",
            "title": "Full Page",
            "status": "current",
            "type": "page",
            "body": {"storage": {"value": "<p>Content</p>" * 100}}
        },
        {
            "id": "456",
            "title": "Empty Page",
            "status": "current",
            "type": "page",
            "body": {"storage": {"value": "<p>Hi</p>"}}  # Less than 50 chars
        }
    ])
    
    with patch("src.core.bulk_tag_orchestrator.AgentModeResolver") as mock_resolver:
        mock_resolver.resolve_mode.return_value = AgentMode.PROD
        mock_resolver.resolve_whitelist.return_value = []
        mock_resolver.can_modify_confluence.return_value = True
        
        orchestrator = BulkTagOrchestrator(
            confluence_client=mock_confluence_client,
            tagging_agent=mock_tagging_agent
        )
        
        result = await orchestrator.tag_space(
            space_key="TEST",
            dry_run_override=False,
            exclude_empty_pages=True
        )
        
        # Verify empty page was skipped
        assert result["skipped_count"] == 1
        assert "empty" in result["skipped_pages"][0]["reason"].lower()


@pytest.mark.asyncio
async def test_bulk_tag_space_limits_tags_per_category(
    mock_confluence_client
):
    """
    Тест: застосування limit_tags_per_category.
    """
    # Mock agent that returns many tags
    mock_agent = MagicMock()
    mock_agent.suggest_tags = AsyncMock(return_value={
        "doc": ["doc-tech", "doc-business", "doc-process", "doc-architecture"],  # 4 tags
        "domain": ["domain-helpdesk-site"],
        "kb": [],
        "tool": []
    })
    
    mock_confluence_client.get_pages_in_space = AsyncMock(return_value=[
        {
            "id": "123",
            "title": "Test Page",
            "status": "current",
            "type": "page",
            "body": {"storage": {"value": "<p>Content</p>" * 100}}
        }
    ])
    
    with patch("src.core.bulk_tag_orchestrator.AgentModeResolver") as mock_resolver:
        mock_resolver.resolve_mode.return_value = AgentMode.PROD
        mock_resolver.resolve_whitelist.return_value = []
        mock_resolver.can_modify_confluence.return_value = True
        
        orchestrator = BulkTagOrchestrator(
            confluence_client=mock_confluence_client,
            tagging_agent=mock_agent
        )
        
        result = await orchestrator.tag_space(
            space_key="TEST",
            dry_run_override=True  # Use dry_run to inspect proposed tags
        )
        
        # Verify tag limiting (MAX_TAGS_PER_CATEGORY = 3)
        page_result = result["details"][0]
        doc_tags = [tag for tag in page_result["tags"]["proposed"] if tag.startswith("doc-")]
        
        # Should be limited to 3 tags per category
        assert len(doc_tags) <= 3


@pytest.mark.asyncio
async def test_bulk_tag_space_handles_ai_errors(
    mock_confluence_client
):
    """
    Тест: обробка помилок AI.
    """
    mock_agent = MagicMock()
    mock_agent.suggest_tags = AsyncMock(side_effect=Exception("AI Error"))
    
    mock_confluence_client.get_pages_in_space = AsyncMock(return_value=[
        {
            "id": "123",
            "title": "Test Page",
            "status": "current",
            "type": "page",
            "body": {"storage": {"value": "<p>Content</p>" * 100}}
        }
    ])
    
    with patch("src.core.bulk_tag_orchestrator.AgentModeResolver") as mock_resolver:
        mock_resolver.resolve_mode.return_value = AgentMode.PROD
        mock_resolver.resolve_whitelist.return_value = []
        
        orchestrator = BulkTagOrchestrator(
            confluence_client=mock_confluence_client,
            tagging_agent=mock_agent
        )
        
        result = await orchestrator.tag_space(
            space_key="TEST",
            dry_run_override=False
        )
        
        # Verify error handling
        assert result["errors"] == 1
        assert result["details"][0]["status"] == "error"
        assert "AI Error" in result["details"][0]["error"]


@pytest.mark.asyncio
async def test_bulk_tag_space_handles_confluence_errors(
    mock_tagging_agent
):
    """
    Тест: обробка помилок Confluence API.
    """
    mock_client = MagicMock()
    mock_client.get_pages_in_space = AsyncMock(
        side_effect=Exception("Confluence API Error")
    )
    
    with patch("src.core.bulk_tag_orchestrator.AgentModeResolver") as mock_resolver:
        mock_resolver.resolve_mode.return_value = AgentMode.PROD
        mock_resolver.resolve_whitelist.return_value = []
        
        orchestrator = BulkTagOrchestrator(
            confluence_client=mock_client,
            tagging_agent=mock_tagging_agent
        )
        
        result = await orchestrator.tag_space(
            space_key="TEST",
            dry_run_override=False
        )
        
        # Verify error handling
        assert result["errors"] == 1
        assert "Confluence API Error" in result.get("error", "")


@pytest.mark.asyncio
async def test_bulk_tag_space_unified_tag_structure(
    mock_confluence_client,
    mock_tagging_agent
):
    """
    Тест: уніфікована структура тегів у відповіді.
    """
    with patch("src.core.bulk_tag_orchestrator.AgentModeResolver") as mock_resolver:
        mock_resolver.resolve_mode.return_value = AgentMode.PROD
        mock_resolver.resolve_whitelist.return_value = []
        mock_resolver.can_modify_confluence.return_value = True
        
        orchestrator = BulkTagOrchestrator(
            confluence_client=mock_confluence_client,
            tagging_agent=mock_tagging_agent
        )
        
        result = await orchestrator.tag_space(
            space_key="TEST",
            dry_run_override=True
        )
        
        # Verify unified structure
        page_result = result["details"][0]
        tags = page_result["tags"]
        
        assert "proposed" in tags
        assert "existing" in tags
        assert "to_add" in tags
        assert "added" in tags
        assert "skipped" in tags
        assert "errors" in tags
        
        # In dry-run: to_add filled, added empty
        assert isinstance(tags["to_add"], list)
        assert tags["added"] == []
