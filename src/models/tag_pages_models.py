"""
Моделі для ендпоінту /bulk/tag-pages
"""

from pydantic import BaseModel, Field
from typing import List, Optional


class TagPagesRequest(BaseModel):
    """
    Модель запиту для тегування списку сторінок.
    
    Attributes:
        space_key: Ключ Confluence простору (використовується для whitelist lookup)
        page_ids: Список ID сторінок для тегування
        dry_run: Якщо True, виконується симуляція без реальних змін (default: True)
    """
    space_key: str = Field(
        ...,
        description="Ключ Confluence простору (використовується для whitelist lookup)",
        example="nkfedba"
    )
    page_ids: List[str] = Field(
        ...,
        description="Список ID Confluence сторінок для тегування",
        example=["19699862097", "19729285121"]
    )
    dry_run: Optional[bool] = Field(
        True,
        description="Якщо True, виконує симуляцію без реальних змін"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "space_key": "nkfedba",
                "page_ids": ["19699862097", "19729285121"],
                "dry_run": True
            }
        }
