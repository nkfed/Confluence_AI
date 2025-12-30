"""
Перевірка валідності JSON конфігурації whitelist.
"""

import json

try:
    with open('src/core/whitelist/whitelist_config.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print('✅ JSON валідний')
    print(f'Просторів: {len(data["spaces"])}')
    
    for space in data["spaces"]:
        space_key = space["space_key"]
        pages_count = len(space["pages"])
        print(f'  - {space_key}: {pages_count} сторінок')

except json.JSONDecodeError as e:
    print(f'❌ JSON невалідний: {e}')
except Exception as e:
    print(f'❌ Помилка: {e}')
