"""
Централізовані налаштування для системи тегування.

Цей модуль містить глобальні константи для управління поведінкою тегування
у всіх агентах та endpoints.
"""

# Максимальна кількість тегів на категорію
# Змініть це значення, щоб глобально контролювати кількість тегів
MAX_TAGS_PER_CATEGORY = 3

# Категорії тегів
TAG_CATEGORIES = ["doc", "domain", "kb", "tool"]

# Опис категорій для документації
TAG_CATEGORY_DESCRIPTIONS = {
    "doc": "Тип документа (doc-tech, doc-business, doc-architecture, ...)",
    "domain": "Домен/проєкт (domain-helpdesk-site, domain-ai-integration, ...)",
    "kb": "Роль у базі знань (kb-overview, kb-canonical, kb-components, ...)",
    "tool": "Інструменти/технології (tool-rovo-agent, tool-confluence, ...)"
}
