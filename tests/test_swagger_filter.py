"""
Тестовий скрипт для симуляції запиту зі Swagger.
Показує детальне логування для діагностики проблеми з фільтрацією.
"""

import asyncio
import httpx

async def test_filter():
    base_url = "http://localhost:8000"
    
    print("=" * 80)
    print("ТЕСТ 1: Запит БЕЗ фільтрів")
    print("=" * 80)
    
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{base_url}/spaces")
        result = response.json()
        
        print(f"Status: {response.status_code}")
        print(f"Spaces count: {len(result.get('spaces', []))}")
        print(f"Spaces:")
        for space in result.get('spaces', [])[:5]:  # Показати перші 5
            print(f"  - {space.get('key')}: type={space.get('type')}, status={space.get('status')}")
    
    print("\n" + "=" * 80)
    print("ТЕСТ 2: Запит З ФІЛЬТРОМ exclude_types=personal")
    print("=" * 80)
    
    async with httpx.AsyncClient() as client:
        # Спосіб 1: як query parameter
        response = await client.get(
            f"{base_url}/spaces",
            params={"exclude_types": "personal"}
        )
        result = response.json()
        
        print(f"Status: {response.status_code}")
        print(f"Request URL: {response.url}")
        print(f"Spaces count: {len(result.get('spaces', []))}")
        print(f"Spaces:")
        for space in result.get('spaces', [])[:5]:
            print(f"  - {space.get('key')}: type={space.get('type')}, status={space.get('status')}")
        
        # Перевірка: чи є personal у результатах?
        has_personal = any(s.get('type') == 'personal' for s in result.get('spaces', []))
        print(f"\n❌ Has personal spaces: {has_personal} (should be False)")
    
    print("\n" + "=" * 80)
    print("ТЕСТ 3: Запит З ФІЛЬТРОМ exclude_statuses=archived")
    print("=" * 80)
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{base_url}/spaces",
            params={"exclude_statuses": "archived"}
        )
        result = response.json()
        
        print(f"Status: {response.status_code}")
        print(f"Spaces count: {len(result.get('spaces', []))}")
        
        has_archived = any(s.get('status') == 'archived' for s in result.get('spaces', []))
        print(f"❌ Has archived spaces: {has_archived} (should be False)")
    
    print("\n" + "=" * 80)
    print("ТЕСТ 4: Запит З ОБОМА ФІЛЬТРАМИ")
    print("=" * 80)
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{base_url}/spaces",
            params={
                "exclude_types": "personal",
                "exclude_statuses": "archived"
            }
        )
        result = response.json()
        
        print(f"Status: {response.status_code}")
        print(f"Spaces count: {len(result.get('spaces', []))}")
        
        has_personal = any(s.get('type') == 'personal' for s in result.get('spaces', []))
        has_archived = any(s.get('status') == 'archived' for s in result.get('spaces', []))
        print(f"❌ Has personal: {has_personal} (should be False)")
        print(f"❌ Has archived: {has_archived} (should be False)")

if __name__ == "__main__":
    asyncio.run(test_filter())
