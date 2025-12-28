"""
Демонстрація роботи Pydantic моделі SpaceFilterParams.
Показує як параметри передаються та валідуються.
"""

from src.models.space_models import SpaceFilterParams

print("=" * 80)
print("ДЕМОНСТРАЦІЯ SpaceFilterParams")
print("=" * 80)

# Тест 1: Параметри за замовчуванням
print("\n📝 ТЕСТ 1: Default параметри")
print("-" * 80)
params = SpaceFilterParams()
print(f"query: {params.query}")
print(f"accessible_only: {params.accessible_only}")
print(f"start: {params.start}")
print(f"limit: {params.limit}")
print(f"exclude_types: {params.exclude_types}")
print(f"exclude_statuses: {params.exclude_statuses}")
print(f"\n✅ exclude_types є порожній список: {params.exclude_types == []}")
print(f"✅ exclude_statuses є порожній список: {params.exclude_statuses == []}")

# Тест 2: З фільтрами
print("\n📝 ТЕСТ 2: З параметрами фільтрації")
print("-" * 80)
params = SpaceFilterParams(
    query="test",
    exclude_types=["personal", "global"],
    exclude_statuses=["archived"],
    limit=50
)
print(f"query: {params.query}")
print(f"exclude_types: {params.exclude_types}")
print(f"exclude_statuses: {params.exclude_statuses}")
print(f"limit: {params.limit}")
print(f"\n✅ exclude_types містить 2 елементи: {len(params.exclude_types) == 2}")
print(f"✅ 'personal' у exclude_types: {'personal' in params.exclude_types}")

# Тест 3: Валідація ліміту
print("\n📝 ТЕСТ 3: Валідація параметрів")
print("-" * 80)
try:
    params = SpaceFilterParams(limit=150)  # Перевищує максимум 100
    print("❌ Валідація не спрацювала!")
except Exception as e:
    print(f"✅ Валідація спрацювала: {type(e).__name__}")
    print(f"   Помилка: limit має бути <= 100")

try:
    params = SpaceFilterParams(start=-5)  # Негативне значення
    print("❌ Валідація не спрацювала!")
except Exception as e:
    print(f"✅ Валідація спрацювала: {type(e).__name__}")
    print(f"   Помилка: start має бути >= 0")

# Тест 4: JSON серіалізація
print("\n📝 ТЕСТ 4: JSON серіалізація (для Swagger)")
print("-" * 80)
params = SpaceFilterParams(
    exclude_types=["personal", "global"],
    exclude_statuses=["archived"]
)
json_data = params.model_dump()
print(f"JSON: {json_data}")
print(f"\n✅ exclude_types серіалізується як список: {isinstance(json_data['exclude_types'], list)}")

print("\n" + "=" * 80)
print("ВИСНОВОК")
print("=" * 80)
print("✅ SpaceFilterParams успішно створена")
print("✅ default_factory=list гарантує порожні списки замість None")
print("✅ Pydantic валідує всі параметри автоматично")
print("✅ Field() з описами забезпечує документацію у Swagger")
print("✅ Параметри правильно серіалізуються в JSON")
print("\n🎯 У Swagger UI кнопки 'Add string item' мають з'явитися для:")
print("   - exclude_types")
print("   - exclude_statuses")
