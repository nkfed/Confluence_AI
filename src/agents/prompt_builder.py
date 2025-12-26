"""
Prompt builder for constructing AI prompts with dynamic content.
"""
from typing import List
from src.utils.prompt_loader import PromptLoader


class PromptBuilder:
    """Builder for constructing AI prompts from templates and dynamic content."""
    
    @staticmethod
    def build_tag_tree_prompt(content: str, allowed_labels: List[str], dry_run: bool = False) -> str:
        """
        Build prompt for tag-tree operation with dynamic whitelist.
        
        Structure:
        - base.txt (tagging/base.txt)
        - ALLOWED TAGS section with dynamic whitelist (plain text, NOT JSON)
        - test.txt or prod.txt depending on dry_run
        - Instruction to tag the PAGE ITSELF, not content as data
        
        Args:
            content: Page content to analyze
            allowed_labels: List of allowed tags for this section
            dry_run: If True, use test.txt mode, otherwise prod.txt
            
        Returns:
            Complete prompt string ready for AI
            
        Example:
            >>> prompt = PromptBuilder.build_tag_tree_prompt(
            ...     content="Some page content",
            ...     allowed_labels=["doc-tech", "kb-overview"],
            ...     dry_run=True
            ... )
        """
        # Load base template
        base_template = PromptLoader.load("tagging", filename="base.txt")
        
        # Build ALLOWED TAGS section (plain text, each tag on new line)
        allowed_tags_section = "ALLOWED TAGS:\n" + "\n".join(f"- {label}" for label in allowed_labels)
        
        # Add explicit instruction about tagging behavior
        tagging_instruction = """
IMPORTANT INSTRUCTIONS:
1. Tag the PAGE ITSELF based on what it contains, not the content as data or hyperlinks.
2. For example, if a page describes a REST API endpoint, tag it as "doc-tech", not as "api-endpoint-data".
3. If a page is an index or root page with mostly links, tag it based on the section it belongs to.
4. Use ONLY tags from the ALLOWED TAGS list above.
5. Do NOT create new tags or use tags not in the list."""
        
        # Load mode-specific template (test or prod)
        mode_filename = "test.txt" if dry_run else "prod.txt"
        mode_template = PromptLoader.load("tagging", filename=mode_filename)
        
        # Construct final prompt
        prompt = f"""{base_template}

{allowed_tags_section}

{tagging_instruction}

{mode_template}

CONTENT TO ANALYZE:
{content[:5000]}

Return ONLY JSON with selected tags from the ALLOWED TAGS list above.
Do not include any tags that are not in the ALLOWED TAGS list."""
        
        return prompt
    
    @staticmethod
    def build_tag_pages_prompt(content: str, dry_run: bool = False) -> str:
        """
        Build prompt for tag-pages operation (legacy, uses policy.txt).
        
        This method maintains backward compatibility with /bulk/tag-pages endpoint.
        
        Args:
            content: Page content to analyze
            dry_run: If True, use test.txt mode, otherwise prod.txt
            
        Returns:
            Complete prompt string ready for AI
        """
        # Load base template
        base_template = PromptLoader.load("tagging", filename="base.txt")
        
        # Load policy template
        policy_template = PromptLoader.load("tagging", filename="policy.txt")
        
        # Load mode-specific template
        mode_filename = "test.txt" if dry_run else "prod.txt"
        mode_template = PromptLoader.load("tagging", filename=mode_filename)
        
        # Construct final prompt
        prompt = f"""{base_template}

{policy_template}

{mode_template}

CONTENT TO ANALYZE:
{content[:5000]}

Return ONLY JSON with selected tags."""
        
        return prompt
