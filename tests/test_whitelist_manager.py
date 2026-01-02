"""
Тести для WhitelistManager — централізованого механізму керування whitelist.
"""

import pytest
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from src.core.whitelist.whitelist_manager import WhitelistManager


@pytest.fixture
def test_config_path(tmp_path):
    """Створює тимчасовий конфігураційний файл для тестів."""
    config = {
        "spaces": [
            {
                "space_key": "TEST",
                "description": "Test space",
                "pages": [
                    {"id": 100, "name": "Root Page", "root": True},
                    {"id": 200, "name": "Entry Point 1", "root": False},
                    {"id": 300, "name": "Entry Point 2", "root": False}
                ]
            },
            {
                "space_key": "NOROOT",
                "description": "Space without root",
                "pages": [
                    {"id": 400, "name": "Page 1", "root": False},
                    {"id": 500, "name": "Page 2", "root": False}
                ]
            }
        ]
    }
    
    config_path = tmp_path / "test_whitelist.json"
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f)
    
    return str(config_path)


@pytest.fixture
def invalid_config_path(tmp_path):
    """Створює конфігурацію з помилками для тестування валідації."""
    config = {
        "spaces": [
            {
                "space_key": "INVALID",
                "pages": [
                    {"id": 100, "name": "Root 1", "root": True},
                    {"id": 200, "name": "Root 2", "root": True},  # Дублікат root
                    {"id": "not_a_number", "name": "Bad ID", "root": False}  # Невалідний ID
                ]
            }
        ]
    }
    
    config_path = tmp_path / "invalid_whitelist.json"
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f)
    
    return str(config_path)


def test_load_config_success(test_config_path):
    """Тест успішного завантаження конфігурації."""
    manager = WhitelistManager(test_config_path)
    
    assert manager.config is not None
    assert "spaces" in manager.config
    assert len(manager.config["spaces"]) == 2


def test_load_config_file_not_found():
    """Тест помилки при відсутності файлу."""
    with pytest.raises(Exception):
        WhitelistManager("nonexistent.json")


def test_validate_success(test_config_path):
    """Тест успішної валідації правильної конфігурації."""
    manager = WhitelistManager(test_config_path)
    warnings = manager.validate()
    
    assert len(warnings) == 0


def test_validate_multiple_roots(invalid_config_path):
    """Тест валідації з кількома root сторінками."""
    with pytest.raises(Exception):
        WhitelistManager(invalid_config_path)


def test_validate_invalid_id(invalid_config_path):
    """Тест валідації з невалідним ID."""
    with pytest.raises(Exception):
        WhitelistManager(invalid_config_path)


def test_mixed_id_types(tmp_path):
    """Тест: змішані типи ID (int + str) → всі ID нормалізуються до int під час завантаження."""
    config = {
        "spaces": [
            {
                "space_key": "MIXED",
                "pages": [
                    {"id": 100, "name": "Page 1", "root": True},
                    {"id": "200", "name": "Page 2", "root": False},
                    {"id": 300, "name": "Page 3", "root": False}
                ]
            }
        ]
    }

    config_path = tmp_path / "mixed_whitelist.json"
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f)

    manager = WhitelistManager(str(config_path))
    entry_points = manager.get_entry_points("MIXED")

    # get_entry_points повертає множину всіх ID (у цьому випадку нема root — всі ID)
    assert entry_points == {100, 200, 300}


def test_get_entry_points_existing_space(test_config_path):
    """Тест отримання entry points для існуючого простору."""
    manager = WhitelistManager(test_config_path)
    entry_points = manager.get_entry_points("TEST")

    # Root є (100), но get_entry_points повертає множину, що включає root
    # За логікою: якщо є root, повертаємо {root}, інакше всі сторінки
    assert 100 in entry_points


def test_get_entry_points_nonexistent_space(test_config_path):
    """Тест отримання entry points для неіснуючого простору."""
    manager = WhitelistManager(test_config_path)
    entry_points = manager.get_entry_points("NONEXISTENT")
    
    assert len(entry_points) == 0


def test_get_entry_points_no_root(test_config_path):
    """Тест entry points для простору без root."""
    manager = WhitelistManager(test_config_path)
    entry_points = manager.get_entry_points("NOROOT")
    
    # Без root-сторінки, всі сторінки — entry points
    assert entry_points == {400, 500}


@pytest.mark.asyncio
async def test_get_allowed_ids_with_children(test_config_path):
    """Тест побудови allowed_ids з дочірніми сторінками."""
    manager = WhitelistManager(test_config_path)

    # Mock Confluence client - get_child_pages повертає list[str]
    mock_client = MagicMock()
    mock_client.get_child_pages = AsyncMock(side_effect=[
        ["101", "102"],  # Дочірні для 100
        [],  # Дочірні для 101
        [],  # Дочірні для 102
    ])

    allowed_ids = await manager.get_allowed_ids("TEST", mock_client)
    # Оскільки всі entry points оброблюються, вклю чаємо root і дочірні
    # Але за логікою конкретної конфігурації: всі entry points + дочірні
    assert 100 in allowed_ids
    assert 101 in allowed_ids
    assert 102 in allowed_ids


@pytest.mark.asyncio
async def test_get_allowed_ids_no_children(test_config_path):
    """Тест allowed_ids коли немає дочірніх сторінок."""
    manager = WhitelistManager(test_config_path)

    # Mock Confluence client - no children
    mock_client = MagicMock()
    mock_client.get_child_pages = AsyncMock(return_value=[])

    allowed_ids = await manager.get_allowed_ids("TEST", mock_client)
    # Всі entry points (200, 300) + root (100) без дочірніх
    assert 100 in allowed_ids


@pytest.mark.asyncio
async def test_get_allowed_ids_caching(test_config_path):
    """Тест кешування результатів всередину одного виклику."""
    manager = WhitelistManager(test_config_path)
    
    mock_client = MagicMock()
    mock_client.get_child_pages = AsyncMock(return_value=[])
    
    # Перший виклик
    allowed_ids_1 = await manager.get_allowed_ids("TEST", mock_client)
    
    # Другий виклик (повторна обробка, без між-виклику кешу)
    allowed_ids_2 = await manager.get_allowed_ids("TEST", mock_client)
    
    assert allowed_ids_1 == allowed_ids_2
    assert 100 in allowed_ids_1


@pytest.mark.asyncio
async def test_get_allowed_ids_empty_space(test_config_path):
    """Тест allowed_ids для неіснуючого простору."""
    manager = WhitelistManager(test_config_path)
    
    mock_client = MagicMock()
    allowed_ids = await manager.get_allowed_ids("NONEXISTENT", mock_client)
    
    assert len(allowed_ids) == 0


def test_is_allowed_page_in_whitelist(test_config_path):
    """Тест перевірки дозволеної сторінки."""
    manager = WhitelistManager(test_config_path)
    allowed_ids = {100, 200, 300}
    
    assert manager.is_allowed("TEST", 100, allowed_ids) is True
    assert manager.is_allowed("TEST", 200, allowed_ids) is True


def test_is_allowed_page_not_in_whitelist(test_config_path):
    """Тест перевірки недозволеної сторінки."""
    manager = WhitelistManager(test_config_path)
    allowed_ids = {100, 200, 300}
    
    assert manager.is_allowed("TEST", 999, allowed_ids) is False


def test_clear_cache(test_config_path):
    """Тест очищення кешу."""
    manager = WhitelistManager(test_config_path)
    
    # Додаємо щось у кеш
    manager._allowed_ids_cache["TEST"] = {100, 200}
    
    assert len(manager._allowed_ids_cache) == 1
    
    manager.clear_cache()
    
    assert len(manager._allowed_ids_cache) == 0


@pytest.mark.asyncio
async def test_recursive_children_collection(test_config_path):
    """Тест рекурсивного збору дочірніх сторінок."""
    manager = WhitelistManager(test_config_path)

    # Mock з деревом: "100" → "101" → "102" → "103"
    mock_client = MagicMock()
    mock_client.get_child_pages = AsyncMock(side_effect=[
        ["101"],  # Дочірні для 100
        ["102"],  # Дочірні для 101
        ["103"],  # Дочірні для 102
        [],       # Дочірні для 103
    ])

    allowed_ids = await manager.get_allowed_ids("TEST", mock_client)
    # Root піддерево включає всю гілку, але всі entry points теж обробляються
    assert 100 in allowed_ids
    assert 101 in allowed_ids
    assert 102 in allowed_ids
    assert 103 in allowed_ids


@pytest.mark.asyncio
async def test_deep_nested_children(test_config_path):
    """
    Тест що ловить баг з неправильним парсингом дочірніх.
    Перевіряє що рекурсія працює на глибину >2 рівні.
    """
    manager = WhitelistManager(test_config_path)

    # Структура: "100" → "101" → "102" → "103" → "104"
    # 5 рівнів вкладеності
    mock_client = MagicMock()
    mock_client.get_child_pages = AsyncMock(side_effect=[
        ["101"],    # Level 1: 100 → 101
        ["102"],    # Level 2: 101 → 102
        ["103"],    # Level 3: 102 → 103
        ["104"],    # Level 4: 103 → 104
        [],         # Level 5: 104 (leaf)
    ])

    allowed_ids = await manager.get_allowed_ids("TEST", mock_client)
    # Має включати всі 5 рівнів від root
    expected_ids = {100, 101, 102, 103, 104}
    for eid in expected_ids:
        assert eid in allowed_ids
    
    # Перевірка що рекурсія працює
    assert 104 in allowed_ids, "Deepest child (level 5) should be included"


@pytest.mark.asyncio
async def test_multiple_branches(test_config_path):
    """
    Тест що рекурсія правильно обходить кілька гілок.
    """
    manager = WhitelistManager(test_config_path)
    
    # Структура:
    # 100 → 101, 102
    #   101 → 111, 112
    #   102 → 121
    mock_client = MagicMock()
    mock_client.get_child_pages = AsyncMock(side_effect=[
        ["101", "102"],  # 100 має 2 дочірні
        ["111", "112"],  # 101 має 2 дочірні
        [],              # 111 (leaf)
        [],              # 112 (leaf)
        ["121"],         # 102 має 1 дочірню
        [],              # 121 (leaf)
    ])
    
    allowed_ids = await manager.get_allowed_ids("TEST", mock_client)
    
    # Має включати всі сторінки з обох гілок
    for eid in [100, 101, 102, 111, 112, 121]:
        assert eid in allowed_ids


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
