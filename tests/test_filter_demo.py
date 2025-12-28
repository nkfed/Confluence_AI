"""
Тест-демонстрація роботи фільтрації просторів.
Перевіряє що простори з exclude_types та exclude_statuses НЕ з'являються у результаті.
"""

from src.services.space_service import SpaceService

# Створити тестові дані
test_spaces = [
    {"id": "1", "key": "GLOBAL_CURRENT", "name": "Global Current", "type": "global", "status": "current"},
    {"id": "2", "key": "PERSONAL_CURRENT", "name": "Personal Current", "type": "personal", "status": "current"},
    {"id": "3", "key": "COLLABORATION_CURRENT", "name": "Collab Current", "type": "collaboration", "status": "current"},
    {"id": "4", "key": "GLOBAL_ARCHIVED", "name": "Global Archived", "type": "global", "status": "archived"},
    {"id": "5", "key": "PERSONAL_ARCHIVED", "name": "Personal Archived", "type": "personal", "status": "archived"},
]

service = SpaceService()

print("=" * 80)
print("ТЕСТ ФІЛЬТРАЦІЇ ПРОСТОРІВ")
print("=" * 80)

print("\n📋 Початковий список просторів:")
for space in test_spaces:
    print(f"  - {space['key']}: type={space['type']}, status={space['status']}")

print(f"\n📊 Всього просторів: {len(test_spaces)}")

# Тест 1: Виключити personal та collaboration
print("\n" + "=" * 80)
print("ТЕСТ 1: exclude_types=['personal', 'collaboration']")
print("=" * 80)

filtered = service.filter_spaces(
    test_spaces,
    exclude_types=['personal', 'collaboration'],
    exclude_statuses=[]
)

print(f"\n✅ Результат ({len(filtered)} просторів):")
for space in filtered:
    print(f"  - {space['key']}: type={space['type']}, status={space['status']}")

print("\n🔍 Перевірка:")
types_in_result = [s['type'] for s in filtered]
print(f"  - 'personal' у результаті: {'personal' in types_in_result} (має бути False)")
print(f"  - 'collaboration' у результаті: {'collaboration' in types_in_result} (має бути False)")

assert 'personal' not in types_in_result, "❌ ПОМИЛКА: 'personal' не має бути у результаті!"
assert 'collaboration' not in types_in_result, "❌ ПОМИЛКА: 'collaboration' не має бути у результаті!"
print("  ✅ Типи виключені правильно!")

# Тест 2: Виключити archived
print("\n" + "=" * 80)
print("ТЕСТ 2: exclude_statuses=['archived']")
print("=" * 80)

filtered = service.filter_spaces(
    test_spaces,
    exclude_types=[],
    exclude_statuses=['archived']
)

print(f"\n✅ Результат ({len(filtered)} просторів):")
for space in filtered:
    print(f"  - {space['key']}: type={space['type']}, status={space['status']}")

print("\n🔍 Перевірка:")
statuses_in_result = [s['status'] for s in filtered]
print(f"  - 'archived' у результаті: {'archived' in statuses_in_result} (має бути False)")

assert 'archived' not in statuses_in_result, "❌ ПОМИЛКА: 'archived' не має бути у результаті!"
print("  ✅ Статуси виключені правильно!")

# Тест 3: OR логіка - виключити personal АБО archived
print("\n" + "=" * 80)
print("ТЕСТ 3: exclude_types=['personal', 'collaboration'] AND exclude_statuses=['archived'] (OR логіка)")
print("=" * 80)

filtered = service.filter_spaces(
    test_spaces,
    exclude_types=['personal', 'collaboration'],
    exclude_statuses=['archived']
)

print(f"\n✅ Результат ({len(filtered)} просторів):")
for space in filtered:
    print(f"  - {space['key']}: type={space['type']}, status={space['status']}")

print("\n🔍 Перевірка OR логіки:")
for space in filtered:
    is_excluded_type = space['type'] in ['personal', 'collaboration']
    is_excluded_status = space['status'] in ['archived']
    print(f"  - {space['key']}: excluded_type={is_excluded_type}, excluded_status={is_excluded_status}")
    assert not is_excluded_type, f"❌ ПОМИЛКА: {space['key']} має тип що виключений!"
    assert not is_excluded_status, f"❌ ПОМИЛКА: {space['key']} має статус що виключений!"

print("  ✅ OR логіка працює правильно!")

# Тест 4: Порожні фільтри
print("\n" + "=" * 80)
print("ТЕСТ 4: exclude_types=[] AND exclude_statuses=[] (без фільтрів)")
print("=" * 80)

filtered = service.filter_spaces(
    test_spaces,
    exclude_types=[],
    exclude_statuses=[]
)

print(f"\n✅ Результат ({len(filtered)} просторів):")
print(f"  - Має бути {len(test_spaces)} просторів (всі)")

assert len(filtered) == len(test_spaces), "❌ ПОМИЛКА: Без фільтрів мають повернутись всі простори!"
print("  ✅ Без фільтрів всі простори повернулись!")

# Фінальний результат
print("\n" + "=" * 80)
print("🎉 ВСІ ТЕСТИ ПРОЙШЛИ УСПІШНО!")
print("=" * 80)
print("\n✅ Фільтрація працює правильно:")
print("  - Виключені типи НЕ з'являються у результаті")
print("  - Виключені статуси НЕ з'являються у результаті")
print("  - OR логіка працює коректно")
print("  - Порожні фільтри повертають всі простори")
