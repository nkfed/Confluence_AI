from typing import Dict, Any, List
from .base_agent import BaseAgent
from .prompt_builder import PromptBuilder
from src.clients.confluence_client import ConfluenceClient
from src.clients.openai_client import OpenAIClient
from src.utils.html_to_text import html_to_text
from src.utils.token_counter import estimate_tokens_count
from src.core.logging.logger import get_logger, audit_logger
from src.core.logging.timing import log_timing
from src.utils.prompt_loader import PromptLoader
import json
import re

logger = get_logger(__name__)

# Minimum content threshold for AI tagging
MIN_CONTENT_THRESHOLD = 200  # characters


class SummaryAgent(BaseAgent):
    """Агент, який формує summary для сторінок Confluence."""

    def __init__(self, confluence_client: ConfluenceClient = None, openai_client: OpenAIClient = None):
        super().__init__()
        self.confluence = confluence_client or ConfluenceClient()
        self.ai = openai_client or OpenAIClient()

    @log_timing
    async def generate_summary(self, page_id: str) -> str:
        """
        Повний пайплайн генерації summary згідно з кроками логування.
        """
        logger.info(f"Step 1: Fetching Confluence page (page_id={page_id})")
        page = await self.confluence.get_page(page_id)

        html_content = page.get("body", {}).get("storage", {}).get("value", "")
        logger.info(f"Step 2: Converting HTML to text (html_length={len(html_content)})")

        text = html_to_text(html_content)
        logger.info(f"Step 2.1: Text extracted (text_length={len(text)})")

        logger.info("Step 3: Estimating tokens")
        approx_tokens = estimate_tokens_count(text)
        logger.info(f"Step 3.1: Estimated tokens = {approx_tokens}")

        logger.info("Step 4: Building prompt for OpenAI")
        prompt_template = PromptLoader.load("summary", mode=self.mode)
        prompt = prompt_template.format(TEXT=text[:5000])

        logger.info("Step 5: Calling OpenAI")
        summary = await self.ai.generate(prompt)

        logger.info("Step 6: Summary generated successfully")
        return summary

    async def process_page(self, page_id: str) -> Dict[str, Any]:
        """
        Обгортка над generate_summary для отримання додаткових метаданих.
        """
        # Отримуємо сторінку ще раз для title, або можна було б передати її з generate_summary.
        # Але згідно з шаблоном, generate_summary сам фетчить сторінку.
        # Щоб не фетчити двічі, ми можемо трохи змінити логіку, 
        # але завдання вимагає саме такий generate_summary.
        
        # Для отримання title спочатку фетчимо (або беремо з generate_summary, якщо змінити його)
        page = await self.confluence.get_page(page_id)
        title = page.get("title")
        
        summary = await self.generate_summary(page_id)
        
        # Отримуємо оцінку токенів (можемо взяти з тексту знову, або передати через контекст)
        html_body = page.get("body", {}).get("storage", {}).get("value", "")
        clean_text = html_to_text(html_body)
        token_estimate = estimate_tokens_count(clean_text)

        return {
            "page_id": page_id,
            "title": title,
            "summary": summary,
            "summary_tokens_estimate": token_estimate
        }

    async def update_page_with_summary(self, page_id: str) -> Dict[str, Any]:
        """
        Оновлює сторінку Confluence, додаючи summary внизу.
        """
        audit_logger.info(
            f"action=update_page_with_summary page_id={page_id} mode={self.mode} started"
        )

        self.enforce_page_policy(page_id)

        result = await self.process_page(page_id)

        summary_html = (
            "<h2>AI Summary</h2>"
            f"<p>{result['summary'].replace('\n', '<br>')}</p>"
        )

        updated_page = self.confluence.append_to_page(
            page_id=page_id,
            html_block=summary_html
        )

        audit_logger.info(
            f"action=update_page_with_summary page_id={page_id} mode={self.mode} status=success"
        )

        return {
            "status": "updated",
            "page_id": page_id,
            "title": result["title"],
            "summary_added": True,
            "summary_tokens_estimate": result["summary_tokens_estimate"]
        }

    async def generate_tags_for_tree(
        self, 
        content: str, 
        allowed_labels: List[str], 
        dry_run: bool = False,
        page_id: str = None
    ) -> List[str]:
        """
        Generate tags for tag-tree operation with dynamic whitelist filtering.
        
        This method:
        1. Checks if content is sufficient for AI tagging
        2. Falls back to section tags for low-content pages (root/index pages)
        3. Uses PromptBuilder to construct prompt with dynamic whitelist
        4. Calls AI to get suggested tags
        5. Deduplicates AI tags while preserving order
        6. Filters deduplicated tags to only include allowed_labels
        7. Returns filtered tags
        
        Fallback conditions (returns allowed_labels):
        - Content is None or empty
        - Content length < MIN_CONTENT_THRESHOLD (200 chars)
        - Content contains only hyperlinks
        
        Args:
            content: Page content to analyze
            allowed_labels: List of allowed tags for this section
            dry_run: If True, use test mode prompts
            page_id: Optional page ID for logging
            
        Returns:
            List of filtered, deduplicated tags that are both suggested by AI and in allowed_labels
            
        Example:
            >>> tags = await agent.generate_tags_for_tree(
            ...     content="Technical documentation about prompts",
            ...     allowed_labels=["doc-tech", "doc-prompt-template", "kb-overview"],
            ...     dry_run=True
            ... )
            >>> # Returns: ["doc-tech", "doc-prompt-template"]
        """
        logger.info(f"Generating tags for tree (dry_run={dry_run}, allowed_labels_count={len(allowed_labels)}, page_id={page_id})")
        logger.debug(f"Allowed labels: {allowed_labels}")
        
        # Check for fallback conditions
        # BUT: Skip fallback if content contains tag-like patterns (likely a tag table/reference page)
        has_tag_patterns = bool(re.search(r"\b(doc-|domain-|tool-|kb-)", content or ""))
        
        if has_tag_patterns:
            logger.info(f"Skipping fallback for page {page_id}: detected tag-like patterns in content (likely a tag table)")
        
        # Fallback condition 1: Empty content
        if not content or len(content.strip()) == 0:
            logger.info(f"Fallback to section tags for page {page_id}: empty content")
            return list(allowed_labels)
        
        # Fallback condition 2: Low content WITHOUT tag patterns
        if len(content) < MIN_CONTENT_THRESHOLD and not has_tag_patterns:
            logger.info(f"Fallback to section tags for page {page_id}: low-content page (length={len(content)} < {MIN_CONTENT_THRESHOLD})")
            return list(allowed_labels)
        
        # Fallback condition 3: Content with only hyperlinks (and no tag patterns)
        content_without_urls = re.sub(r'https?://[^\s]+', '', content)
        if len(content_without_urls.strip()) < MIN_CONTENT_THRESHOLD and not has_tag_patterns:
            logger.info(f"Fallback to section tags for page {page_id}: content contains mostly hyperlinks")
            return list(allowed_labels)
        
        # Build prompt using PromptBuilder
        prompt = PromptBuilder.build_tag_tree_prompt(content, allowed_labels, dry_run)
        
        # Call AI
        logger.info("Calling OpenAI for tag suggestions")
        ai_response = await self.ai.generate(prompt)
        logger.debug(f"AI response: {ai_response[:500]}")
        
        # Parse AI response (expecting JSON with tags)
        ai_tags = self._parse_tags_from_response(ai_response)
        logger.info(f"AI suggested {len(ai_tags)} tags (with potential duplicates): {ai_tags}")
        
        # Deduplicate while preserving order (BEFORE filtering)
        unique_tags = []
        for tag in ai_tags:
            if tag not in unique_tags:
                unique_tags.append(tag)
        
        if len(ai_tags) != len(unique_tags):
            duplicates_count = len(ai_tags) - len(unique_tags)
            logger.info(f"Removed {duplicates_count} duplicate tags. Deduplicated: {unique_tags}")
        
        # Filter deduplicated tags to only include those in allowed_labels (AFTER dedupe)
        filtered_tags = []
        for tag in unique_tags:
            if tag in allowed_labels:
                filtered_tags.append(tag)
        
        logger.info(f"Filtered to {len(filtered_tags)} allowed tags: {filtered_tags}")
        
        if len(unique_tags) > len(filtered_tags):
            removed_tags = [tag for tag in unique_tags if tag not in allowed_labels]
            logger.warning(f"Removed {len(removed_tags)} disallowed tags: {removed_tags}")
        
        return filtered_tags
    
    def _parse_tags_from_response(self, response: str) -> List[str]:
        """
        Parse tags from AI response.
        
        Expects JSON format like:
        {"doc": ["doc-tech"], "domain": ["domain-helpdesk-site"], ...}
        
        Returns flat list of all tags.
        """
        # Try to extract JSON from response
        match = re.search(r"\{.*\}", response, re.DOTALL)
        if not match:
            logger.warning("No JSON found in AI response")
            return []
        
        try:
            data = json.loads(match.group(0))
            # Flatten all tags from all categories
            tags = []
            for category_tags in data.values():
                if isinstance(category_tags, list):
                    tags.extend(category_tags)
            return tags
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from AI response: {e}")
            return []