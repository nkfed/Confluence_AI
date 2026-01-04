"""
Prompt builder for constructing AI prompts with dynamic content.
"""
from typing import List
from src.utils.prompt_loader import PromptLoader
from src.config.tagging_settings import MAX_TAGS_PER_CATEGORY, TAG_CATEGORIES


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
            allowed_labels: List of allowed tags for this section.
                            If empty [], all tags are allowed (unbounded mode for tag-tree)
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
        from src.config.tagging_settings import TAG_CATEGORIES
        
        # Load base template
        base_template = PromptLoader.load("tagging", filename="base.txt")
        
        # ✅ ВАЖЛИВО: Якщо allowed_labels порожня, це означає "без обмеження"
        # Генеруємо повний список всіх можливих тегів
        if not allowed_labels:
            # Generate all possible tags by category (prefix-based)
            # For unbounded mode, we tell AI to use standard tag prefixes
            allowed_labels_text = """ALLOWED TAGS (All Standard Tags):
- All tags starting with: doc-, domain-, kb-, tool-

Examples:
- doc-tech, doc-business, doc-process, doc-requirements, doc-onboarding, doc-architecture, doc-template, doc-prompt-template, doc-ai-tools
- domain-ehealth-core, domain-ai-integration, domain-helpdesk-site, domain-rehab-1-0, domain-rehab-2-0
- kb-overview, kb-canonical, kb-components, kb-template
- tool-confluence, tool-vscode, tool-pycharm, tool-rovo-agent, tool-gemini, tool-openai"""
        else:
            # Build ALLOWED TAGS section (plain text, each tag on new line)
            allowed_labels_text = "ALLOWED TAGS:\n" + "\n".join(f"- {label}" for label in allowed_labels)
        
        # Build dynamic limit instruction using config
        limit_instruction = f"""
ВАЖЛИВО:
Для кожної категорії тегів ({", ".join(TAG_CATEGORIES)}) пропонуй не більше {MAX_TAGS_PER_CATEGORY} найбільш релевантних тегів.
Не повертай повні списки можливих тегів.
Пріоритет — точність і релевантність, а не повнота."""
        
        # Add explicit instruction about tagging behavior
        tagging_instruction = """

ІНСТРУКЦІЇ З ТЕГУВАННЯ:
1. Тегуй САМУ СТОРІНКУ на основі того, що вона містить, а не контент як дані чи гіперпосилання.
2. Наприклад, якщо сторінка описує REST API endpoint, тегуй її як "doc-tech", а не як "api-endpoint-data".
3. Якщо сторінка є індексом або кореневою сторінкою з переважно посиланнями, тегуй її на основі розділу, до якого вона належить.
4. Використовуй теги зі списку ALLOWED TAGS вище.
5. НЕ створюй нові теги."""
        
        # Load mode-specific template (test or prod)
        mode_filename = "test.txt" if dry_run else "prod.txt"
        mode_template = PromptLoader.load("tagging", filename=mode_filename)
        
        # Construct final prompt
        prompt = f"""{base_template}

{allowed_labels_text}

{limit_instruction}

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
        
        # Build dynamic limit instruction using config
        limit_instruction = f"""
ВАЖЛИВО:
Для кожної категорії тегів ({", ".join(TAG_CATEGORIES)}) пропонуй не більше {MAX_TAGS_PER_CATEGORY} найбільш релевантних тегів.
Не повертай повні списки можливих тегів.
Пріоритет — точність і релевантність, а не повнота."""
        
        # Load mode-specific template
        mode_filename = "test.txt" if dry_run else "prod.txt"
        mode_template = PromptLoader.load("tagging", filename=mode_filename)
        
        # Construct final prompt
        prompt = f"""{base_template}

{policy_template}

{limit_instruction}

{mode_template}

CONTENT TO ANALYZE:
{content[:5000]}

Return ONLY JSON with selected tags."""
        
        return prompt
