"""
Test для перевірки правила ≤3 теги на категорію в TaggingAgent
"""
import pytest
import asyncio
from src.agents.tagging_agent import TaggingAgent
from src.core.logging.logging_config import configure_logging

configure_logging()


@pytest.mark.asyncio
async def test_tagging_agent_max_3_tags_per_category():
    """
    Перевірка правила: не більше 3 тегів на категорію (doc, domain, kb, tool).
    
    Expected:
    - Кожна категорія містить ≤ 3 теги
    - AI не повертає повні списки можливих тегів
    """
    print(f"\n[TEST] Testing TaggingAgent ≤3 tags per category rule")
    
    # Великий текст для генерації багатьох тегів
    large_text = """
    Це технічна документація про архітектуру системи Helpdesk для медичних реєстрів.
    Система використовує штучний інтелект для обробки запитів користувачів.
    Основні компоненти включають:
    - Rovo Agent для інтелектуального аналізу
    - Confluence для зберігання документації
    - GitHub Copilot для підтримки розробників
    - VS Code як основне середовище розробки
    
    База знань містить:
    - Канонічні документи з архітектури
    - Огляди компонентів системи
    - Індекс всіх доступних ресурсів
    - Ієрархію сутностей
    - UML діаграми
    
    Домени:
    - Helpdesk site
    - AI Integration
    - Rehab 2.0
    - eHealth Core
    - ДЗР
    """
    
    agent = TaggingAgent()
    
    print(f"  Mode: {agent.mode}")
    print(f"  Text length: {len(large_text)} chars")
    
    # Generate tags
    tags = await agent.suggest_tags(large_text)
    
    print(f"\n[TEST] Generated tags:")
    print(f"  doc: {tags.get('doc', [])} (count: {len(tags.get('doc', []))})")
    print(f"  domain: {tags.get('domain', [])} (count: {len(tags.get('domain', []))})")
    print(f"  kb: {tags.get('kb', [])} (count: {len(tags.get('kb', []))})")
    print(f"  tool: {tags.get('tool', [])} (count: {len(tags.get('tool', []))})")
    
    # Verify ≤3 tags per category
    for category, tag_list in tags.items():
        count = len(tag_list)
        print(f"\n  Verifying {category}: {count} tags")
        
        assert isinstance(tag_list, list), f"{category} should be a list"
        assert count <= 3, f"{category} has {count} tags, should be ≤3"
        
        print(f"    ✅ {category}: {count} ≤ 3")
    
    # Verify total not overwhelming
    total_tags = sum(len(tag_list) for tag_list in tags.values())
    print(f"\n  Total tags: {total_tags}")
    assert total_tags <= 12, f"Total tags {total_tags} exceeds maximum 12 (3 per category × 4 categories)"
    
    print(f"\n[TEST] ✅ All categories comply with ≤3 tags rule!")
    
    return tags


@pytest.mark.asyncio
async def test_tagging_agent_empty_page_no_full_lists():
    """
    Перевірка на порожній сторінці: AI не повертає повний список тегів.
    
    Expected:
    - На порожніх сторінках tags містять мінімум тегів
    - Не повертається повний список можливих тегів
    """
    print(f"\n[TEST] Testing empty page - no full tag lists")
    
    # Порожній або майже порожній текст
    empty_text = ""
    
    agent = TaggingAgent()
    
    print(f"  Mode: {agent.mode}")
    print(f"  Text: (empty)")
    
    # Generate tags for empty page
    tags = await agent.suggest_tags(empty_text)
    
    print(f"\n[TEST] Generated tags for empty page:")
    print(f"  doc: {tags.get('doc', [])} (count: {len(tags.get('doc', []))})")
    print(f"  domain: {tags.get('domain', [])} (count: {len(tags.get('domain', []))})")
    print(f"  kb: {tags.get('kb', [])} (count: {len(tags.get('kb', []))})")
    print(f"  tool: {tags.get('tool', [])} (count: {len(tags.get('tool', []))})")
    
    # Verify minimal tags (not full lists)
    total_tags = sum(len(tag_list) for tag_list in tags.values())
    print(f"\n  Total tags: {total_tags}")
    
    # Empty page should have very few tags (0-3)
    assert total_tags <= 3, f"Empty page returned {total_tags} tags, expected ≤3"
    
    print(f"\n[TEST] ✅ Empty page correctly returned minimal tags (not full lists)!")
    
    return tags


@pytest.mark.asyncio
async def test_tagging_agent_consistency_across_modes():
    """
    Перевірка консистентності правила ≤3 теги в різних режимах.
    
    Expected:
    - TEST, SAFE_TEST, PROD - всі дотримуються правила ≤3 теги
    """
    print(f"\n[TEST] Testing ≤3 tags rule consistency across all modes")
    
    test_text = """
    Документація системи для медичних реєстрів з використанням AI.
    Архітектура включає компоненти Helpdesk та інтеграції.
    """
    
    # Test different modes (if accessible)
    import os
    original_mode = os.getenv("TAGGING_AGENT_MODE")
    
    for mode in ["TEST", "SAFE_TEST", "PROD"]:
        os.environ["TAGGING_AGENT_MODE"] = mode
        
        print(f"\n  Testing mode: {mode}")
        
        agent = TaggingAgent()
        tags = await agent.suggest_tags(test_text)
        
        # Verify each category
        for category, tag_list in tags.items():
            count = len(tag_list)
            assert count <= 3, f"{mode} mode: {category} has {count} tags, should be ≤3"
            print(f"    {category}: {count} tags ✅")
    
    # Reset
    if original_mode:
        os.environ["TAGGING_AGENT_MODE"] = original_mode
    
    print(f"\n[TEST] ✅ All modes comply with ≤3 tags rule!")


if __name__ == "__main__":
    print("="*80)
    print("TAGGING AGENT ≤3 TAGS RULE TEST")
    print("="*80)
    
    print("\n" + "="*80)
    print("TEST 1: MAX 3 TAGS PER CATEGORY")
    print("="*80)
    asyncio.run(test_tagging_agent_max_3_tags_per_category())
    
    print("\n" + "="*80)
    print("TEST 2: EMPTY PAGE - NO FULL LISTS")
    print("="*80)
    asyncio.run(test_tagging_agent_empty_page_no_full_lists())
    
    print("\n" + "="*80)
    print("TEST 3: CONSISTENCY ACROSS MODES")
    print("="*80)
    asyncio.run(test_tagging_agent_consistency_across_modes())
    
    print("\n" + "="*80)
    print("✅ ALL ≤3 TAGS RULE TESTS PASSED!")
    print("="*80)
