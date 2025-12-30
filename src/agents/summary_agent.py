from typing import Dict, Any, List, Optional
from .base_agent import BaseAgent
from .prompt_builder import PromptBuilder
from src.clients.confluence_client import ConfluenceClient
from src.clients.openai_client import OpenAIClient
from src.core.ai.router import AIProviderRouter
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

    def __init__(
        self,
        confluence_client: ConfluenceClient = None,
        openai_client: OpenAIClient = None,
        ai_router: Optional[AIProviderRouter] = None,
        ai_provider: Optional[str] = None
    ):
        super().__init__(agent_name="SUMMARY_AGENT")
        self.confluence = confluence_client or ConfluenceClient()
        
        # Support both old (openai_client) and new (ai_router) initialization
        if ai_router is not None:
            self._ai_router = ai_router
            self._ai_provider = ai_provider
            self.ai = None  # Mark as using router
            logger.info(f"SummaryAgent using AI Router with provider: {ai_provider or 'default'}")
        else:
            # Backward compatibility: use direct OpenAI client
            self.ai = openai_client or OpenAIClient()
            self._ai_router = None
            self._ai_provider = None
            logger.info("SummaryAgent using direct OpenAI client (legacy mode)")
        
        # Debug logging for mode verification
        print(f"DEBUG: SummaryAgent initialized with mode={self.mode}")
        print(f"DEBUG: SummaryAgent allowed_test_pages={self.allowed_test_pages}")
        logger.info(f"SummaryAgent initialized: mode={self.mode}, allowed_pages={len(self.allowed_test_pages)}")

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

        logger.info("Step 4: Building prompt for AI")
        prompt_template = PromptLoader.load("summary", mode=self.mode)
        prompt = prompt_template.format(TEXT=text[:5000])

        logger.info("Step 5: Calling AI provider")
        if self._ai_router is not None:
            # Use router
            provider = self._ai_router.get(self._ai_provider)
            ai_response = await provider.generate(prompt)
            summary = ai_response.text
            logger.info(f"Step 5.1: AI response received (provider={ai_response.provider}, tokens={ai_response.total_tokens})")
        else:
            # Legacy: direct OpenAI call
            summary = await self.ai.generate(prompt)
            logger.info("Step 5.1: OpenAI response received (legacy mode)")

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

        # Centralized dry-run logic based on mode
        if self.is_dry_run():
            # TEST mode: dry-run, no Confluence changes
            logger.info(f"[DRY-RUN] TEST mode - summary NOT written to Confluence")
            logger.info(f"[DRY-RUN] Would append summary to page {page_id}")
            logger.debug(f"[DRY-RUN] Summary HTML length: {len(summary_html)} chars")
            
            audit_logger.info(
                f"action=update_page_with_summary page_id={page_id} mode={self.mode} status=dry_run"
            )
            
            return {
                "status": "dry_run",
                "page_id": page_id,
                "title": result["title"],
                "summary_added": False,
                "summary_tokens_estimate": result["summary_tokens_estimate"],
                "message": "TEST mode - summary NOT written to Confluence"
            }

        # SAFE_TEST or PROD mode - actually update Confluence
        logger.info(f"[{self.mode}] Appending summary to page {page_id}")
        updated_page = await self.confluence.append_to_page(
            page_id=page_id,
            html_block=summary_html
        )
        
        logger.info(f"Summary appended to page {page_id}. Response keys: {list(updated_page.keys())}")
        logger.debug(f"Confluence response: {updated_page.get('id')}, version: {updated_page.get('version', {}).get('number')}")

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
            # ✅ Apply limit to fallback tags
            return self._limit_fallback_tags(allowed_labels)
        
        # Fallback condition 2: Low content WITHOUT tag patterns
        if len(content) < MIN_CONTENT_THRESHOLD and not has_tag_patterns:
            logger.info(f"Fallback to section tags for page {page_id}: low-content page (length={len(content)} < {MIN_CONTENT_THRESHOLD})")
            # ✅ Apply limit to fallback tags
            return self._limit_fallback_tags(allowed_labels)
        
        # Fallback condition 3: Content with only hyperlinks (and no tag patterns)
        content_without_urls = re.sub(r'https?://[^\s]+', '', content)
        if len(content_without_urls.strip()) < MIN_CONTENT_THRESHOLD and not has_tag_patterns:
            logger.info(f"Fallback to section tags for page {page_id}: content contains mostly hyperlinks")
            # ✅ Apply limit to fallback tags
            return self._limit_fallback_tags(allowed_labels)
        
        # Build prompt using PromptBuilder
        prompt = PromptBuilder.build_tag_tree_prompt(content, allowed_labels, dry_run)
        
        # Call AI
        logger.info("Calling OpenAI for tag suggestions")
        ai_response = await self.ai.generate(prompt)
        logger.debug(f"AI response: {ai_response[:500]}")
        
        # Parse AI response (expecting JSON with tags by category)
        ai_tags_dict = self._parse_tags_dict_from_response(ai_response)
        logger.info(f"AI suggested tags by category: {ai_tags_dict}")
        
        # ✅ Step 1: Apply MAX_TAGS_PER_CATEGORY limit (post-processing)
        from src.utils.tag_structure import limit_tags_per_category
        from src.config.tagging_settings import MAX_TAGS_PER_CATEGORY
        
        limited_tags_dict = limit_tags_per_category(ai_tags_dict)
        
        if ai_tags_dict != limited_tags_dict:
            logger.warning(
                f"AI returned more than {MAX_TAGS_PER_CATEGORY} tags per category. "
                f"Applied post-processing limit. Original: {ai_tags_dict}, Limited: {limited_tags_dict}"
            )
        
        # ✅ Step 2: Flatten to list
        ai_tags = []
        for category_tags in limited_tags_dict.values():
            if isinstance(category_tags, list):
                ai_tags.extend(category_tags)
        
        logger.info(f"Flattened limited tags: {ai_tags} (count={len(ai_tags)})")
        
        # ✅ Step 3: Deduplicate while preserving order
        unique_tags = []
        for tag in ai_tags:
            if tag not in unique_tags:
                unique_tags.append(tag)
        
        if len(ai_tags) != len(unique_tags):
            duplicates_count = len(ai_tags) - len(unique_tags)
            logger.info(f"Removed {duplicates_count} duplicate tags. Deduplicated: {unique_tags}")
        
        # ✅ Step 4: Filter to only include allowed_labels
        filtered_tags = []
        for tag in unique_tags:
            if tag in allowed_labels:
                filtered_tags.append(tag)
        
        logger.info(f"Filtered to {len(filtered_tags)} allowed tags: {filtered_tags}")
        
        if len(unique_tags) > len(filtered_tags):
            removed_tags = [tag for tag in unique_tags if tag not in allowed_labels]
            logger.warning(f"Removed {len(removed_tags)} disallowed tags: {removed_tags}")
        
        return filtered_tags
    
    def _parse_tags_dict_from_response(self, response: str) -> dict:
        """
        Parse tags from AI response as dictionary by category.
        
        Expects JSON format like:
        {"doc": ["doc-tech"], "domain": ["domain-helpdesk-site"], ...}
        
        Returns dict with tags by category.
        """
        from src.config.tagging_settings import TAG_CATEGORIES
        
        # Try to extract JSON from response
        match = re.search(r"\{.*\}", response, re.DOTALL)
        if not match:
            logger.warning("No JSON found in AI response")
            return {cat: [] for cat in TAG_CATEGORIES}
        
        try:
            data = json.loads(match.group(0))
            # Ensure all categories exist
            result = {cat: [] for cat in TAG_CATEGORIES}
            for category in TAG_CATEGORIES:
                if category in data and isinstance(data[category], list):
                    result[category] = data[category]
            return result
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from AI response: {e}")
            return {cat: [] for cat in TAG_CATEGORIES}
    
    def _parse_tags_from_response(self, response: str) -> List[str]:
        """
        Parse tags from AI response (legacy method - flattens to list).
        
        Expects JSON format like:
        {"doc": ["doc-tech"], "domain": ["domain-helpdesk-site"], ...}
        
        Returns flat list of all tags.
        """
        tags_dict = self._parse_tags_dict_from_response(response)
        # Flatten all tags
        tags = []
        for category_tags in tags_dict.values():
            if isinstance(category_tags, list):
                tags.extend(category_tags)
        return tags
    def _limit_fallback_tags(self, allowed_labels: List[str]) -> List[str]:
        """
        Обмежує fallback теги згідно з MAX_TAGS_PER_CATEGORY.
        
        Для fallback (порожні сторінки, root pages) ми не можемо викликати AI,
        тому повертаємо перші N тегів з кожної категорії з allowed_labels.
        
        Args:
            allowed_labels: Список дозволених тегів
            
        Returns:
            Обмежений список тегів (≤MAX_TAGS_PER_CATEGORY на категорію)
        """
        from src.config.tagging_settings import MAX_TAGS_PER_CATEGORY, TAG_CATEGORIES
        
        # Group by category
        by_category = {cat: [] for cat in TAG_CATEGORIES}
        for label in allowed_labels:
            for cat in TAG_CATEGORIES:
                if label.startswith(f"{cat}-"):
                    by_category[cat].append(label)
                    break
        
        # Limit each category
        limited_tags = []
        for cat in TAG_CATEGORIES:
            cat_tags = by_category[cat][:MAX_TAGS_PER_CATEGORY]
            limited_tags.extend(cat_tags)
        
        logger.info(f"Fallback tags limited from {len(allowed_labels)} to {len(limited_tags)} (≤{MAX_TAGS_PER_CATEGORY} per category)")
        
        return limited_tags
