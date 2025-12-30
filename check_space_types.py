"""
Скрипт для перевірки які типи та статуси просторів є у Confluence.
"""

import asyncio
import httpx

async def check_space_types():
    base_url = "http://localhost:8000"
    
    print("=" * 80)
    print("ПЕРЕВІРКА ТИПІВ ТА СТАТУСІВ ПРОСТОРІВ")
    print("=" * 80)
    
    # Отримати метадані
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{base_url}/spaces/meta")
        meta = response.json()
        
        print("\n📊 Доступні типи просторів:")
        for space_type in meta.get('available_types', []):
            print(f"  - {space_type}")
        
        print("\n📊 Доступні статуси просторів:")
        for status in meta.get('available_statuses', []):
            print(f"  - {status}")
    
    # Отримати всі простори
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{base_url}/spaces", params={"limit": 100})
        result = response.json()
        
        spaces = result.get('spaces', [])
        print(f"\n📈 Всього просторів: {len(spaces)}")
        
        # Підрахувати по типах
        type_counts = {}
        for space in spaces:
            space_type = space.get('type', 'unknown')
            type_counts[space_type] = type_counts.get(space_type, 0) + 1
        
        print("\n📊 Розподіл по типах:")
        for space_type, count in sorted(type_counts.items()):
            percentage = (count / len(spaces) * 100) if spaces else 0
            print(f"  - {space_type}: {count} ({percentage:.1f}%)")
        
        # Підрахувати по статусах
        status_counts = {}
        for space in spaces:
            status = space.get('status', 'unknown')
            status_counts[status] = status_counts.get(status, 0) + 1
        
        print("\n📊 Розподіл по статусах:")
        for status, count in sorted(status_counts.items()):
            percentage = (count / len(spaces) * 100) if spaces else 0
            print(f"  - {status}: {count} ({percentage:.1f}%)")
        
        # Показати декілька прикладів НЕ personal просторів
        non_personal = [s for s in spaces if s.get('type') != 'personal']
        print(f"\n📋 НЕ personal простори ({len(non_personal)}):")
        for space in non_personal[:5]:
            print(f"  - {space.get('key')}: type={space.get('type')}, status={space.get('status')}")
        
        # Показати декілька прикладів НЕ archived просторів
        non_archived = [s for s in spaces if s.get('status') != 'archived']
        print(f"\n📋 НЕ archived простори ({len(non_archived)}):")
        for space in non_archived[:5]:
            print(f"  - {space.get('key')}: type={space.get('type')}, status={space.get('status')}")
    
    print("\n" + "=" * 80)
    print("ВИСНОВОК")
    print("=" * 80)
    
    if len(non_personal) == 0:
        print("⚠️  У вас НЕ має non-personal просторів!")
        print("   Тому exclude_types=personal дає 0 результатів - це ПРАВИЛЬНО")
    else:
        print(f"✅ У вас є {len(non_personal)} non-personal просторів")
    
    if len(non_archived) == 0:
        print("⚠️  У вас НЕ має non-archived просторів!")
        print("   Тому exclude_statuses=archived дає 0 результатів - це ПРАВИЛЬНО")
    else:
        print(f"✅ У вас є {len(non_archived)} non-archived просторів")

if __name__ == "__main__":
    asyncio.run(check_space_types())
