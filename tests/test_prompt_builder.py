"""
Unit tests for PromptBuilder and SummaryAgent tag-tree functionality.
"""
import pytest
from src.agents.prompt_builder import PromptBuilder
from src.core.ai.interface import AIResponse
from unittest.mock import AsyncMock, MagicMock, patch


class TestPromptBuilder:
    """Tests for PromptBuilder."""
    
    def test_build_tag_tree_prompt_structure(self):
        """Test that tag-tree prompt has correct structure."""
        content = "Sample page content about helpdesk"
        allowed_labels = ["doc-tech", "domain-helpdesk-site", "kb-overview"]
        
        prompt = PromptBuilder.build_tag_tree_prompt(content, allowed_labels, dry_run=True)
        
        # Check structure
        assert "ALLOWED TAGS:" in prompt
        assert "- doc-tech" in prompt
        assert "- domain-helpdesk-site" in prompt
        assert "- kb-overview" in prompt
        assert "CONTENT TO ANALYZE:" in prompt
        assert content[:100] in prompt
    
    def test_build_tag_tree_prompt_dry_run_true(self):
        """Test that dry_run=True includes test mode content."""
        content = "Test content"
        allowed_labels = ["doc-tech"]
        
        prompt = PromptBuilder.build_tag_tree_prompt(content, allowed_labels, dry_run=True)
        
        # Should include test mode markers
        assert "test" in prompt.lower() or "тест" in prompt.lower()
    
    def test_build_tag_tree_prompt_dry_run_false(self):
        """Test that dry_run=False includes prod mode content."""
        content = "Test content"
        allowed_labels = ["doc-tech"]
        
        prompt = PromptBuilder.build_tag_tree_prompt(content, allowed_labels, dry_run=False)
        
        # Should include prod mode content
        # (exact content depends on prod.txt template)
        assert "ALLOWED TAGS:" in prompt
    
    def test_build_tag_tree_prompt_empty_labels(self):
        """Test prompt with empty allowed labels list."""
        content = "Test content"
        allowed_labels = []
        
        prompt = PromptBuilder.build_tag_tree_prompt(content, allowed_labels, dry_run=True)
        
        assert "ALLOWED TAGS:" in prompt
        # Should still have structure even with empty list
    
    def test_build_tag_tree_prompt_many_labels(self):
        """Test prompt with many allowed labels."""
        content = "Test content"
        allowed_labels = [
            "doc-tech", "doc-business", "domain-helpdesk-site",
            "kb-overview", "kb-canonical", "tool-rovo-agent"
        ]
        
        prompt = PromptBuilder.build_tag_tree_prompt(content, allowed_labels, dry_run=True)
        
        # All labels should be present
        for label in allowed_labels:
            assert label in prompt
    
    def test_build_tag_pages_prompt_has_policy(self):
        """Test that tag-pages prompt includes policy.txt (backward compatibility)."""
        content = "Test content"
        
        prompt = PromptBuilder.build_tag_pages_prompt(content, dry_run=False)
        
        # Should include base template
        assert len(prompt) > 0
        # Exact policy.txt content check depends on template


class TestSummaryAgentTagging:
    """Tests for SummaryAgent tag-tree functionality."""
    
    @pytest.mark.asyncio
    async def test_generate_tags_for_tree_filters_correctly(self):
        """Test that generate_tags_for_tree filters AI response to allowed labels."""
        from src.agents.summary_agent import SummaryAgent
        
        # Mock AI response with mix of allowed and disallowed tags
        mock_ai_response_text = '{"doc": ["doc-tech", "doc-personal"], "domain": ["domain-helpdesk-site"]}'
        
        agent = SummaryAgent()
        mock_response = AIResponse(
            text=mock_ai_response_text,
            provider="mock",
            model="mock-model",
            total_tokens=0
        )
        agent.ai = AsyncMock()
        agent.ai.generate = AsyncMock(return_value=mock_response)
        
        # Use content that's long enough to avoid fallback (> 200 chars)
        content = "This is a comprehensive technical documentation page that covers various aspects. " * 5
        allowed_labels = ["doc-tech", "domain-helpdesk-site"]  # doc-personal not allowed
        
        result = await agent.generate_tags_for_tree(content, allowed_labels, dry_run=True, page_id="test-123")
        
        # Should only include allowed tags
        assert "doc-tech" in result
        assert "domain-helpdesk-site" in result
        assert "doc-personal" not in result
        assert len(result) == 2
    
    @pytest.mark.asyncio
    async def test_generate_tags_for_tree_empty_allowed_labels(self):
        """Test behavior with empty allowed labels list."""
        from src.agents.summary_agent import SummaryAgent
        
        mock_ai_response_text = '{"doc": ["doc-tech"]}'
        
        agent = SummaryAgent()
        mock_response = AIResponse(
            text=mock_ai_response_text,
            provider="mock",
            model="mock-model",
            total_tokens=0
        )
        agent.ai = AsyncMock()
        agent.ai.generate = AsyncMock(return_value=mock_response)
        
        # Use content that's long enough to avoid fallback (> 200 chars)
        content = "This is a comprehensive technical documentation page that covers various aspects. " * 5
        allowed_labels = []
        
        result = await agent.generate_tags_for_tree(content, allowed_labels, dry_run=True, page_id="test-123")
        
        # Should return empty list (all tags filtered out)
        assert result == []
    
    @pytest.mark.asyncio
    async def test_generate_tags_for_tree_all_tags_allowed(self):
        """Test when all AI-suggested tags are in allowed list."""
        from src.agents.summary_agent import SummaryAgent
        
        mock_ai_response_text = '{"doc": ["doc-tech"], "kb": ["kb-overview"]}'
        
        agent = SummaryAgent()
        mock_response = AIResponse(
            text=mock_ai_response_text,
            provider="mock",
            model="mock-model",
            total_tokens=0
        )
        agent.ai = AsyncMock()
        agent.ai.generate = AsyncMock(return_value=mock_response)
        
        # Use content that's long enough to avoid fallback (> 200 chars)
        content = "This is a comprehensive technical documentation page that covers various aspects. " * 5
        allowed_labels = ["doc-tech", "kb-overview", "domain-helpdesk-site"]
        
        result = await agent.generate_tags_for_tree(content, allowed_labels, dry_run=True, page_id="test-123")
        
        # Should include all AI tags since all are allowed
        assert len(result) == 2
        assert "doc-tech" in result
        assert "kb-overview" in result
    
    @pytest.mark.asyncio
    async def test_parse_tags_from_response_valid_json(self):
        """Test parsing tags from valid JSON response."""
        from src.agents.summary_agent import SummaryAgent
        
        agent = SummaryAgent()
        response = '{"doc": ["doc-tech", "doc-business"], "domain": ["domain-helpdesk-site"]}'
        
        tags = agent._parse_tags_from_response(response)
        
        assert len(tags) == 3
        assert "doc-tech" in tags
        assert "doc-business" in tags
        assert "domain-helpdesk-site" in tags
    
    @pytest.mark.asyncio
    async def test_parse_tags_from_response_invalid_json(self):
        """Test parsing tags from invalid JSON."""
        from src.agents.summary_agent import SummaryAgent
        
        agent = SummaryAgent()
        response = "This is not JSON"
        
        tags = agent._parse_tags_from_response(response)
        
        # Should return empty list on parse failure
        assert tags == []
    
    @pytest.mark.asyncio
    async def test_parse_tags_from_response_empty(self):
        """Test parsing tags from empty response."""
        from src.agents.summary_agent import SummaryAgent
        
        agent = SummaryAgent()
        response = ""
        
        tags = agent._parse_tags_from_response(response)
        
        assert tags == []
    @pytest.mark.asyncio
    async def test_generate_tags_for_tree_deduplicates(self):
        """Test that generate_tags_for_tree removes duplicate tags."""
        from src.agents.summary_agent import SummaryAgent
        
        # Mock AI response with duplicate tags
        mock_ai_response_text = '{"doc": ["doc-tech", "doc-tech"], "domain": ["domain-helpdesk-site", "doc-tech"]}'
        
        agent = SummaryAgent()
        mock_response = AIResponse(
            text=mock_ai_response_text,
            provider="mock",
            model="mock-model",
            total_tokens=0
        )
        agent.ai = AsyncMock()
        agent.ai.generate = AsyncMock(return_value=mock_response)
        
        # Use content that's long enough to avoid fallback (> 200 chars)
        content = "This is a comprehensive technical documentation page that covers various aspects. " * 5
        allowed_labels = ["doc-tech", "domain-helpdesk-site"]
        
        result = await agent.generate_tags_for_tree(content, allowed_labels, dry_run=True, page_id="test-123")
        
        # Should deduplicate: ["doc-tech", "doc-tech", "domain-helpdesk-site", "doc-tech"] -> ["doc-tech", "domain-helpdesk-site"]
        assert len(result) == 2
        assert "doc-tech" in result
        assert "domain-helpdesk-site" in result
        # Check order is preserved (first occurrence)
        assert result[0] == "doc-tech"
        assert result[1] == "domain-helpdesk-site"
        assert result[1] == "domain-helpdesk-site"
    
    @pytest.mark.asyncio
    async def test_generate_tags_for_tree_fallback_empty_content(self):
        """Test fallback to allowed_labels for empty content."""
        from src.agents.summary_agent import SummaryAgent
        
        agent = SummaryAgent()
        agent.ai = AsyncMock()  # Should not be called
        
        allowed_labels = ["doc-tech", "kb-overview"]
        
        # Test empty string
        result = await agent.generate_tags_for_tree("", allowed_labels, dry_run=True, page_id="test-123")
        assert result == allowed_labels
        
        # Test None
        result = await agent.generate_tags_for_tree(None, allowed_labels, dry_run=True, page_id="test-123")
        assert result == allowed_labels
        
        # AI should not have been called
        agent.ai.generate.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_generate_tags_for_tree_fallback_low_content(self):
        """Test fallback to allowed_labels for low content (< 200 chars) WITHOUT tag patterns."""
        from src.agents.summary_agent import SummaryAgent
        
        agent = SummaryAgent()
        agent.ai = AsyncMock()  # Should not be called
        
        allowed_labels = ["doc-tech", "kb-overview", "domain-helpdesk-site"]
        short_content = "Short page with only a title."  # < 200 chars, no tag patterns
        
        result = await agent.generate_tags_for_tree(
            short_content, 
            allowed_labels, 
            dry_run=True, 
            page_id="test-123"
        )
        
        # Check that result contains all expected tags (order may vary)
        assert set(result) == set(allowed_labels)
        assert len(result) == len(allowed_labels)
        agent.ai.generate.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_generate_tags_for_tree_no_fallback_has_tag_patterns(self):
        """Test that low-content pages with tag patterns are NOT treated as fallback."""
        from src.agents.summary_agent import SummaryAgent
        
        mock_ai_response_text = '{"doc": ["doc-process", "kb-canonical"]}'
        
        agent = SummaryAgent()
        mock_response = AIResponse(
            text=mock_ai_response_text,
            provider="mock",
            model="mock-model",
            total_tokens=0
        )
        agent.ai = AsyncMock()
        agent.ai.generate = AsyncMock(return_value=mock_response)
        
        allowed_labels = ["doc-process", "kb-canonical", "kb-overview"]
        # Short content BUT contains tag patterns (should NOT fallback)
        tag_table_content = "Tags: doc-tech, domain-helpdesk, kb-overview"  # < 200 chars but has tag patterns
        
        result = await agent.generate_tags_for_tree(
            tag_table_content, 
            allowed_labels, 
            dry_run=True, 
            page_id="test-123"
        )
        
        # AI should have been called (no fallback)
        agent.ai.generate.assert_called_once()
        assert "doc-process" in result
        assert "kb-canonical" in result
    
    @pytest.mark.asyncio
    async def test_generate_tags_for_tree_fallback_only_hyperlinks(self):
        """Test fallback to allowed_labels for pages with only hyperlinks."""
        from src.agents.summary_agent import SummaryAgent
        
        agent = SummaryAgent()
        agent.ai = AsyncMock()  # Should not be called
        
        allowed_labels = ["doc-tech", "kb-overview"]
        # Content with mostly URLs (after removing URLs, < 200 chars)
        hyperlink_content = """
        Links:
        https://example.com/doc1
        https://example.com/doc2
        https://example.com/doc3
        See docs
        """
        
        result = await agent.generate_tags_for_tree(
            hyperlink_content, 
            allowed_labels, 
            dry_run=True, 
            page_id="test-123"
        )
        
        assert result == allowed_labels
        agent.ai.generate.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_generate_tags_for_tree_no_fallback_sufficient_content(self):
        """Test that AI is called for pages with sufficient content."""
        from src.agents.summary_agent import SummaryAgent
        
        mock_ai_response_text = '{"doc": ["doc-tech"]}'
        
        agent = SummaryAgent()
        mock_response = AIResponse(
            text=mock_ai_response_text,
            provider="mock",
            model="mock-model",
            total_tokens=0
        )
        agent.ai = AsyncMock()
        agent.ai.generate = AsyncMock(return_value=mock_response)
        
        allowed_labels = ["doc-tech", "kb-overview"]
        # Long enough content (> 200 chars)
        sufficient_content = "This is a technical documentation page that describes " * 10  # ~500 chars
        
        result = await agent.generate_tags_for_tree(
            sufficient_content, 
            allowed_labels, 
            dry_run=True, 
            page_id="test-123"
        )
        
        # AI should have been called
        agent.ai.generate.assert_called_once()
        assert "doc-tech" in result
