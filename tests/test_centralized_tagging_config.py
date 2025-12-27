"""
Тест для перевірки централізованого конфігу MAX_TAGS_PER_CATEGORY
"""
import pytest
import asyncio
from src.agents.tagging_agent import TaggingAgent
from src.utils.tag_structure import limit_tags_per_category
from src.agents.prompt_builder import PromptBuilder
from src.config import tagging_settings
from src.core.logging.logging_config import configure_logging

configure_logging()


def test_config_exists():
    """Перевірка що конфіг існує та має правильні значення."""
    print(f"\n[TEST] Checking tagging_settings config")
    
    assert hasattr(tagging_settings, 'MAX_TAGS_PER_CATEGORY'), \
        "Config should have MAX_TAGS_PER_CATEGORY"
    assert hasattr(tagging_settings, 'TAG_CATEGORIES'), \
        "Config should have TAG_CATEGORIES"
    
    print(f"  MAX_TAGS_PER_CATEGORY: {tagging_settings.MAX_TAGS_PER_CATEGORY}")
    print(f"  TAG_CATEGORIES: {tagging_settings.TAG_CATEGORIES}")
    
    assert isinstance(tagging_settings.MAX_TAGS_PER_CATEGORY, int), \
        "MAX_TAGS_PER_CATEGORY should be int"
    assert tagging_settings.MAX_TAGS_PER_CATEGORY > 0, \
        "MAX_TAGS_PER_CATEGORY should be positive"
    assert isinstance(tagging_settings.TAG_CATEGORIES, list), \
        "TAG_CATEGORIES should be list"
    
    print(f"\n[TEST] ✅ Config validation passed!")


def test_limit_tags_per_category_uses_config():
    """Перевірка що limit_tags_per_category використовує конфіг."""
    print(f"\n[TEST] Testing limit_tags_per_category with config")
    
    # Create tags exceeding limit
    tags = {
        "doc": ["doc-tech", "doc-architecture", "doc-business", "doc-process", "doc-onboarding"],
        "domain": ["domain-helpdesk-site", "domain-ai-integration", "domain-ehealth-core", "domain-dzr"],
        "kb": ["kb-overview", "kb-canonical", "kb-components", "kb-index"],
        "tool": ["tool-rovo-agent", "tool-confluence", "tool-vscode", "tool-pycharm"]
    }
    
    print(f"  Original tags per category:")
    for cat, tag_list in tags.items():
        print(f"    {cat}: {len(tag_list)} tags")
    
    # Apply limit
    limited = limit_tags_per_category(tags)
    
    print(f"\n  Limited tags per category:")
    for cat, tag_list in limited.items():
        print(f"    {cat}: {len(tag_list)} tags")
        assert len(tag_list) <= tagging_settings.MAX_TAGS_PER_CATEGORY, \
            f"{cat} has {len(tag_list)} tags, should be ≤{tagging_settings.MAX_TAGS_PER_CATEGORY}"
    
    print(f"\n[TEST] ✅ limit_tags_per_category respects MAX_TAGS_PER_CATEGORY={tagging_settings.MAX_TAGS_PER_CATEGORY}")


def test_prompt_builder_includes_config():
    """Перевірка що PromptBuilder включає MAX_TAGS_PER_CATEGORY у промпт."""
    print(f"\n[TEST] Testing PromptBuilder includes config in prompt")
    
    test_content = "Test page content"
    allowed_labels = ["doc-tech", "kb-overview"]
    
    # Build prompt
    prompt = PromptBuilder.build_tag_tree_prompt(
        content=test_content,
        allowed_labels=allowed_labels,
        dry_run=True
    )
    
    print(f"  Prompt length: {len(prompt)}")
    
    # Check that MAX_TAGS_PER_CATEGORY is mentioned in prompt
    max_value_str = str(tagging_settings.MAX_TAGS_PER_CATEGORY)
    
    assert max_value_str in prompt, \
        f"Prompt should contain MAX_TAGS_PER_CATEGORY value ({max_value_str})"
    
    # Check for Ukrainian instructions
    assert "не більше" in prompt, \
        "Prompt should contain Ukrainian limit instruction"
    
    print(f"  ✅ Found MAX_TAGS_PER_CATEGORY={max_value_str} in prompt")
    print(f"  ✅ Found Ukrainian instructions")
    
    print(f"\n[TEST] ✅ PromptBuilder correctly uses config!")


@pytest.mark.asyncio
async def test_dynamic_config_change():
    """
    Тест демонструє як зміна конфігу впливає на результат.
    
    NOTE: Цей тест НЕ змінює конфіг реально (щоб не впливати на інші тести),
    а лише демонструє що функція limit_tags_per_category працює правильно.
    """
    print(f"\n[TEST] Testing dynamic config change (simulation)")
    
    original_limit = tagging_settings.MAX_TAGS_PER_CATEGORY
    print(f"  Current MAX_TAGS_PER_CATEGORY: {original_limit}")
    
    # Simulate tags with more than current limit
    tags = {
        "doc": ["doc-tech", "doc-architecture", "doc-business", "doc-process"],
        "domain": ["domain-helpdesk-site", "domain-ai-integration"],
        "kb": [],
        "tool": ["tool-rovo-agent", "tool-confluence", "tool-vscode"]
    }
    
    # Apply current limit
    limited = limit_tags_per_category(tags)
    
    print(f"\n  With MAX_TAGS_PER_CATEGORY={original_limit}:")
    for cat, tag_list in limited.items():
        if tag_list:
            print(f"    {cat}: {len(tag_list)} tags = {tag_list}")
            assert len(tag_list) <= original_limit
    
    print(f"\n[TEST] ✅ Dynamic config would work (if we changed tagging_settings.MAX_TAGS_PER_CATEGORY)")
    print(f"  To test with different limit:")
    print(f"  1. Change MAX_TAGS_PER_CATEGORY in src/config/tagging_settings.py")
    print(f"  2. Re-run tests")
    print(f"  3. All prompts and post-processing will automatically use new limit!")


if __name__ == "__main__":
    print("="*80)
    print("CENTRALIZED TAGGING CONFIG TEST")
    print("="*80)
    
    test_config_exists()
    test_limit_tags_per_category_uses_config()
    test_prompt_builder_includes_config()
    asyncio.run(test_dynamic_config_change())
    
    print("\n" + "="*80)
    print("✅ ALL CONFIG TESTS PASSED!")
    print("="*80)
