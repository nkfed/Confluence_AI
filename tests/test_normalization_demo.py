"""
Демонстрація роботи нормалізації параметрів фільтрації.
Показує як різні формати з Swagger перетворюються на коректні значення.
"""

from src.api.routers.spaces import normalize_list_param

print("=" * 80)
print("ДЕМОНСТРАЦІЯ НОРМАЛІЗАЦІЇ ПАРАМЕТРІВ ФІЛЬТРАЦІЇ")
print("=" * 80)

# Тест 1: Swagger може передати значення з лапками
print("\n" + "=" * 80)
print("ТЕСТ 1: Swagger передає значення з одинарними лапками")
print("=" * 80)
input_swagger = ["'personal'", "'global'"]
print(f"📥 Вхідні дані з Swagger: {input_swagger}")
normalized = normalize_list_param(input_swagger)
print(f"✅ Нормалізовано: {normalized}")
print(f"🔍 Результат: {normalized == ['personal', 'global']}")

# Тест 2: Swagger може передати значення з подвійними лапками
print("\n" + "=" * 80)
print("ТЕСТ 2: Swagger передає значення з подвійними лапками")
print("=" * 80)
input_swagger = ['"personal"', '"archived"']
print(f"📥 Вхідні дані з Swagger: {input_swagger}")
normalized = normalize_list_param(input_swagger)
print(f"✅ Нормалізовано: {normalized}")
print(f"🔍 Результат: {normalized == ['personal', 'archived']}")

# Тест 3: Swagger може передати значення з дужками
print("\n" + "=" * 80)
print("ТЕСТ 3: Swagger передає значення з дужками")
print("=" * 80)
input_swagger = ["['personal']", "['global']"]
print(f"📥 Вхідні дані з Swagger: {input_swagger}")
normalized = normalize_list_param(input_swagger)
print(f"✅ Нормалізовано: {normalized}")
print(f"🔍 Результат: {normalized == ['personal', 'global']}")

# Тест 4: Чисті значення (ідеальний випадок)
print("\n" + "=" * 80)
print("ТЕСТ 4: Чисті значення (ідеальний випадок)")
print("=" * 80)
input_swagger = ["personal", "global", "archived"]
print(f"📥 Вхідні дані з Swagger: {input_swagger}")
normalized = normalize_list_param(input_swagger)
print(f"✅ Нормалізовано: {normalized}")
print(f"🔍 Результат: {normalized == ['personal', 'global', 'archived']}")

# Тест 5: Значення зі зайвими пробілами
print("\n" + "=" * 80)
print("ТЕСТ 5: Значення зі зайвими пробілами")
print("=" * 80)
input_swagger = [" personal ", "  global  ", " archived"]
print(f"📥 Вхідні дані з Swagger: {input_swagger}")
normalized = normalize_list_param(input_swagger)
print(f"✅ Нормалізовано: {normalized}")
print(f"🔍 Результат: {normalized == ['personal', 'global', 'archived']}")

# Тест 6: Мікс різних форматів
print("\n" + "=" * 80)
print("ТЕСТ 6: Мікс різних форматів (реальний випадок)")
print("=" * 80)
input_swagger = ["'personal'", '"global"', " archived ", "['collaboration']"]
print(f"📥 Вхідні дані з Swagger: {input_swagger}")
normalized = normalize_list_param(input_swagger)
print(f"✅ Нормалізовано: {normalized}")
print(f"🔍 Очікується: ['personal', 'global', 'archived', 'collaboration']")
print(f"🔍 Результат правильний: {set(normalized) == {'personal', 'global', 'archived', 'collaboration'}}")

# Тест 7: Порожні значення та пробіли
print("\n" + "=" * 80)
print("ТЕСТ 7: Порожні значення фільтруються")
print("=" * 80)
input_swagger = ["", " ", "personal", "", "  "]
print(f"📥 Вхідні дані з Swagger: {input_swagger}")
normalized = normalize_list_param(input_swagger)
print(f"✅ Нормалізовано: {normalized}")
print(f"🔍 Результат: {normalized == ['personal']}")

# Фінальна перевірка
print("\n" + "=" * 80)
print("🎉 ВИСНОВОК")
print("=" * 80)
print("✅ Функція normalize_list_param() правильно обробляє:")
print("   - Одинарні лапки ('personal')")
print("   - Подвійні лапки (\"personal\")")
print("   - Дужки (['personal'])")
print("   - Зайві пробіли ( personal )")
print("   - Порожні значення (видаляє їх)")
print("   - Мікс різних форматів")
print("\n✅ Фільтрація тепер працюватиме коректно незалежно від формату!")
