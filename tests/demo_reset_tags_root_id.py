"""
Демонстрація використання розширеного reset-tags з підтримкою root_id.

Цей скрипт показує різні сценарії використання ендпоінту reset-tags
з новим параметром root_id.
"""

import requests
import json
from typing import Optional


class ResetTagsDemo:
    """Демо-клас для тестування reset-tags функціональності."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        
    def reset_tags(
        self,
        space_key: str,
        root_id: Optional[str] = None,
        categories: Optional[str] = None,
        dry_run: bool = True
    ) -> dict:
        """
        Виклик ендпоінту reset-tags.
        
        Args:
            space_key: Ключ Confluence простору
            root_id: Опціональний ID кореневої сторінки для tree scope
            categories: Категорії тегів для видалення (comma-separated)
            dry_run: Dry-run режим
            
        Returns:
            JSON відповідь від API
        """
        url = f"{self.base_url}/bulk/reset-tags/{space_key}"
        
        params = {"dry_run": dry_run}
        if root_id:
            params["root_id"] = root_id
        if categories:
            params["categories"] = categories
            
        print(f"\n🔄 Виклик: POST {url}")
        print(f"📋 Параметри: {json.dumps(params, indent=2)}")
        
        response = requests.post(url, params=params)
        result = response.json()
        
        print(f"✅ Відповідь ({response.status_code}):")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
        return result


def demo_space_scope():
    """Демо 1: Видалення тегів у всьому просторі (space scope)."""
    print("\n" + "="*70)
    print("📁 DEMO 1: Space Scope — Видалення всіх AI-тегів у просторі")
    print("="*70)
    
    client = ResetTagsDemo()
    
    # Dry-run спочатку
    result = client.reset_tags(
        space_key="TEST",
        dry_run=True
    )
    
    print(f"\n📊 Результат:")
    print(f"   - Scope: {result.get('scope')}")
    print(f"   - Total pages: {result.get('total')}")
    print(f"   - Would remove tags from: {result.get('removed')} pages")
    print(f"   - Pages without tags: {result.get('no_tags')}")


def demo_tree_scope():
    """Демо 2: Видалення тегів в дереві сторінок (tree scope)."""
    print("\n" + "="*70)
    print("🌲 DEMO 2: Tree Scope — Видалення тегів в межах дерева")
    print("="*70)
    
    client = ResetTagsDemo()
    
    # Dry-run з root_id
    result = client.reset_tags(
        space_key="DOCS",
        root_id="123456",
        dry_run=True
    )
    
    print(f"\n📊 Результат:")
    print(f"   - Scope: {result.get('scope')}")
    print(f"   - Root ID: {result.get('root_id')}")
    print(f"   - Pages in tree: {result.get('total')}")
    print(f"   - Would remove tags from: {result.get('removed')} pages")


def demo_tree_scope_with_categories():
    """Демо 3: Видалення тегів вибраних категорій в дереві."""
    print("\n" + "="*70)
    print("🏷️ DEMO 3: Tree Scope + Categories — Вибіркове видалення")
    print("="*70)
    
    client = ResetTagsDemo()
    
    # Видалення лише doc та kb тегів в дереві
    result = client.reset_tags(
        space_key="KB",
        root_id="789012",
        categories="doc,kb",
        dry_run=True
    )
    
    print(f"\n📊 Результат:")
    print(f"   - Scope: {result.get('scope')}")
    print(f"   - Root ID: {result.get('root_id')}")
    print(f"   - Categories: doc, kb")
    print(f"   - Pages in tree: {result.get('total')}")
    print(f"   - Would remove tags from: {result.get('removed')} pages")


def demo_validation_error():
    """Демо 4: Помилка валідації — root_id з іншого простору."""
    print("\n" + "="*70)
    print("❌ DEMO 4: Validation Error — root_id належить іншому простору")
    print("="*70)
    
    client = ResetTagsDemo()
    
    # Спроба використати root_id з іншого простору
    result = client.reset_tags(
        space_key="EXPECTED_SPACE",
        root_id="999999",  # Належить іншому простору
        dry_run=True
    )
    
    print(f"\n📊 Результат:")
    print(f"   - Errors: {result.get('errors')}")
    if result.get('error'):
        print(f"   - Error message: {result.get('error')}")


def demo_production_run():
    """Демо 5: Production run — реальне видалення (dry_run=false)."""
    print("\n" + "="*70)
    print("🚀 DEMO 5: Production Run — Реальне видалення тегів")
    print("="*70)
    print("\n⚠️  УВАГА: Цей приклад виконує РЕАЛЬНЕ видалення тегів!")
    print("    Використовуйте з обережністю!\n")
    
    client = ResetTagsDemo()
    
    # Спочатку dry-run
    print("1️⃣ Крок 1: Dry-run для перевірки")
    dry_result = client.reset_tags(
        space_key="TEST",
        root_id="123456",
        categories="doc",
        dry_run=True
    )
    
    print(f"\n   Буде видалено тегів: {dry_result.get('removed')}")
    
    # Якщо все ОК — виконуємо
    print("\n2️⃣ Крок 2: Виконання (dry_run=false)")
    print("   [Закоментовано для безпеки — розкоментуйте для виконання]\n")
    
    # Розкоментуйте наступні рядки для реального виконання:
    # prod_result = client.reset_tags(
    #     space_key="TEST",
    #     root_id="123456",
    #     categories="doc",
    #     dry_run=False
    # )
    # print(f"   Видалено тегів: {prod_result.get('removed')}")


def demo_comparison():
    """Демо 6: Порівняння Space vs Tree scope."""
    print("\n" + "="*70)
    print("⚖️ DEMO 6: Порівняння Space Scope vs Tree Scope")
    print("="*70)
    
    client = ResetTagsDemo()
    
    print("\n🔹 Space Scope (весь простір):")
    space_result = client.reset_tags(
        space_key="TEST",
        dry_run=True
    )
    
    print("\n🔹 Tree Scope (лише підрозділ):")
    tree_result = client.reset_tags(
        space_key="TEST",
        root_id="123456",
        dry_run=True
    )
    
    print(f"\n📊 Порівняння:")
    print(f"   Space Scope:")
    print(f"      - Total pages: {space_result.get('total')}")
    print(f"      - Would process: {space_result.get('removed')}")
    print(f"   Tree Scope:")
    print(f"      - Total pages: {tree_result.get('total')}")
    print(f"      - Would process: {tree_result.get('removed')}")


def main():
    """Запуск всіх демо-сценаріїв."""
    print("\n" + "="*70)
    print("🎯 RESET-TAGS з ROOT_ID — Демонстрація")
    print("="*70)
    print("\nℹ️  Примітка: Для роботи скрипту повинен працювати сервер на localhost:8000")
    print("   Запустіть: uvicorn src.main:app --reload\n")
    
    try:
        # Перевірка доступності сервера
        response = requests.get("http://localhost:8000/docs", timeout=2)
        if response.status_code != 200:
            print("⚠️  Сервер недоступний. Запустіть API сервер перед демо.\n")
            return
    except Exception as e:
        print(f"⚠️  Помилка підключення до сервера: {e}")
        print("   Запустіть API сервер: uvicorn src.main:app --reload\n")
        return
    
    # Запуск демо
    demos = [
        ("Space Scope", demo_space_scope),
        ("Tree Scope", demo_tree_scope),
        ("Tree + Categories", demo_tree_scope_with_categories),
        ("Validation Error", demo_validation_error),
        ("Production Run", demo_production_run),
        ("Comparison", demo_comparison)
    ]
    
    for name, demo_func in demos:
        try:
            demo_func()
            print(f"\n✅ {name} — завершено")
        except Exception as e:
            print(f"\n❌ {name} — помилка: {e}")
    
    print("\n" + "="*70)
    print("🎉 Демонстрація завершена!")
    print("="*70)
    print("\n📖 Докладніше: docs/RESET_TAGS_ROOT_ID.md")
    print("🧪 Тести: tests/test_reset_tags_root_id.py\n")


if __name__ == "__main__":
    main()
