"""
Pydantic моделі для роботи з просторами Confluence.
"""

from pydantic import BaseModel, Field
from typing import List, Optional


class SpaceFilterParams(BaseModel):
    """
    Параметри фільтрації для ендпоінту GET /spaces.
    
    Використовується через Depends() для правильного відображення у Swagger UI.
    """
    
    query: Optional[str] = Field(
        default=None,
        description="Search query for spaces (spaceKey or name)"
    )
    
    accessible_only: bool = Field(
        default=True,
        description="Return only accessible spaces"
    )
    
    start: int = Field(
        default=0,
        ge=0,
        description="Start index for pagination"
    )
    
    limit: int = Field(
        default=25,
        ge=1,
        le=100,
        description="Maximum number of results (1-100)"
    )
    
    exclude_types: List[str] = Field(
        default_factory=list,
        description="Space types to exclude. Add each value separately. Example: personal, global"
    )
    
    exclude_statuses: List[str] = Field(
        default_factory=list,
        description="Space statuses to exclude. Add each value separately. Example: archived"
    )
    
    name_contains: Optional[str] = Field(
        default=None,
        description="Substring to match in space name (case-insensitive). Example: ЕСОЗ"
    )
