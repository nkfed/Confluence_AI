"""
Демонстрація роботи comma-separated фільтрів.
"""

from src.api.routers.spaces import normalize_list_param

print("=" * 80)
print("ДЕМОНСТРАЦІЯ COMMA-SEPARATED ФІЛЬТРІВ")
print("=" * 80)

# Спосіб 1: Вводити через кому в одне поле (найзручніше!)
print("\n📝 СПОСІБ 1: Ввести у одне поле через кому")
print("   У Swagger вводите: personal, global")
print("   -" * 40)
input_swagger = ["personal, global"]
result = normalize_list_param(input_swagger)
print(f"   Результат: {result}")
print(f"   ✅ Працює: {result == ['personal', 'global']}")

# Спосіб 2: Без пробілів після коми
print("\n📝 СПОСІБ 2: Без пробілів після коми")
print("   У Swagger вводите: personal,global,team")
print("   -" * 40)
input_swagger = ["personal,global,team"]
result = normalize_list_param(input_swagger)
print(f"   Результат: {result}")
print(f"   ✅ Працює: {result == ['personal', 'global', 'team']}")

# Спосіб 3: Натискати "Add string item" для кожного значення
print("\n📝 СПОСІБ 3: Натискати 'Add string item' для кожного")
print("   1. Натиснути 'Add string item'")
print("   2. Ввести: personal")
print("   3. Натиснути 'Add string item' знову")
print("   4. Ввести: global")
print("   -" * 40)
input_swagger = ["personal", "global"]
result = normalize_list_param(input_swagger)
print(f"   Результат: {result}")
print(f"   ✅ Працює: {result == ['personal', 'global']}")

# Спосіб 4: Мікс (деякі через кому, деякі окремо)
print("\n📝 СПОСІБ 4: Мікс (через кому + окремі елементи)")
print("   1. Ввести у перше поле: personal, global")
print("   2. Натиснути 'Add string item'")
print("   3. Ввести у друге поле: archived")
print("   -" * 40)
input_swagger = ["personal, global", "archived"]
result = normalize_list_param(input_swagger)
print(f"   Результат: {result}")
print(f"   ✅ Працює: {result == ['personal', 'global', 'archived']}")

print("\n" + "=" * 80)
print("РЕКОМЕНДАЦІЯ")
print("=" * 80)
print("✅ Найпростіше: вводити через кому в одне поле")
print("   Наприклад: personal, global")
print("   або: personal,global,team")
print("\n✅ Це працює у обох параметрах:")
print("   - exclude_types: personal, global")
print("   - exclude_statuses: archived, current")
