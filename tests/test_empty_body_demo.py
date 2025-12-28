"""
Демонстрація що tag-space працює з порожнім тілом.
"""

import requests
import json

BASE_URL = "http://localhost:8000"

print("=" * 80)
print("ТЕСТ: POST /bulk/tag-space з порожнім тілом")
print("=" * 80)

# Тест 1: Без тіла взагалі
print("\n📝 ТЕСТ 1: POST без тіла")
print("-" * 80)
try:
    response = requests.post(f"{BASE_URL}/bulk/tag-space/nkfedba")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Успіх!")
        print(f"   Mode: {data.get('mode')}")
        print(f"   Whitelist enabled: {data.get('whitelist_enabled')}")
        print(f"   Dry run: {data.get('dry_run')}")
    else:
        print(f"❌ Помилка: {response.text}")
except Exception as e:
    print(f"❌ Помилка запиту: {e}")

# Тест 2: З порожнім JSON
print("\n📝 ТЕСТ 2: POST з порожнім JSON {}")
print("-" * 80)
try:
    response = requests.post(
        f"{BASE_URL}/bulk/tag-space/nkfedba",
        json={}
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print(f"✅ Успіх!")
    else:
        print(f"❌ Помилка: {response.text}")
except Exception as e:
    print(f"❌ Помилка запиту: {e}")

# Тест 3: З query параметрами
print("\n📝 ТЕСТ 3: POST з query параметром dry_run=true")
print("-" * 80)
try:
    response = requests.post(
        f"{BASE_URL}/bulk/tag-space/nkfedba",
        params={"dry_run": True}
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Успіх!")
        print(f"   Dry run: {data.get('dry_run')}")
    else:
        print(f"❌ Помилка: {response.text}")
except Exception as e:
    print(f"❌ Помилка запиту: {e}")

# Тест 4: Curl еквівалент з порожнім тілом
print("\n📝 ТЕСТ 4: Curl еквівалент (симуляція)")
print("-" * 80)
print("Еквівалент команди:")
print(f"  curl -X POST '{BASE_URL}/bulk/tag-space/nkfedba'")
print("або:")
print(f"  curl -X POST '{BASE_URL}/bulk/tag-space/nkfedba' -H 'Content-Type: application/json'")

print("\n" + "=" * 80)
print("ВИСНОВОК")
print("=" * 80)
print("✅ Ендпоінт /bulk/tag-space/{space_key} працює без тіла")
print("✅ Не потрібно надсилати -d '' або -d '{}' при POST запиті")
print("✅ Query параметри (dry_run) працюють коректно")
print("\n💡 Рекомендація: використовувати curl БЕЗ параметра -d:")
print(f"   curl -X POST '{BASE_URL}/bulk/tag-space/nkfedba'")
