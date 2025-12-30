"""
SpaceService — сервіс для роботи з просторами Confluence.

Забезпечує:
- Отримання списку просторів
- Отримання всіх сторінок простору
- Фільтрацію та пагінацію
- Метадані просторів (типи та статуси)
"""

from typing import Dict, Any, List, Optional
from src.clients.confluence_client import ConfluenceClient
from src.core.logging.logger import get_logger

logger = get_logger(__name__)


class SpaceService:
    """Сервіс для роботи з просторами Confluence."""
    
    def __init__(self, confluence_client: ConfluenceClient = None):
        """
        Ініціалізація SpaceService.
        
        Args:
            confluence_client: Клієнт Confluence (опціонально)
        """
        self.confluence = confluence_client or ConfluenceClient()
    
    async def get_all_spaces(self) -> List[Dict[str, Any]]:
        """
        Отримати всі простори без пагінації.
        
        Returns:
            Список всіх просторів з полями id, key, name, type, status
        """
        logger.info("Fetching all spaces without pagination")
        
        all_spaces = []
        start = 0
        limit = 100
        
        try:
            while True:
                data = await self.confluence.get_spaces(
                    query=None,
                    accessible_only=True,
                    start=start,
                    limit=limit
                )
                
                results = data.get("results", [])
                if not results:
                    break
                
                for space_data in results:
                    all_spaces.append({
                        "id": space_data.get("id"),
                        "key": space_data.get("key"),
                        "name": space_data.get("name"),
                        "type": space_data.get("type"),
                        "status": space_data.get("status", "current")
                    })
                
                # Якщо результатів менше ліміту — остання сторінка
                if len(results) < limit:
                    break
                
                start += limit
            
            logger.info(f"Successfully retrieved {len(all_spaces)} spaces in total")
            return all_spaces
            
        except Exception as e:
            logger.error(f"Error getting all spaces: {e}")
            raise
    
    def filter_spaces(
        self,
        spaces: List[Dict[str, Any]],
        exclude_types: Optional[List[str]] = None,
        exclude_statuses: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Фільтрує простори за exclude_types та exclude_statuses.
        
        Логіка OR: виключає простір якщо type ∈ exclude_types АБО status ∈ exclude_statuses
        
        Args:
            spaces: Список просторів
            exclude_types: Типи для виключення
            exclude_statuses: Статуси для виключення
            
        Returns:
            Відфільтрований список просторів
        """
        # Нормалізувати до списків
        exclude_types = exclude_types or []
        exclude_statuses = exclude_statuses or []
        
        # Якщо обидва списки порожні - нічого не фільтрувати
        if len(exclude_types) == 0 and len(exclude_statuses) == 0:
            return spaces
        
        filtered = []
        excluded_count = 0
        
        for space in spaces:
            space_type = space.get("type", "")
            space_status = space.get("status", "")
            
            # OR логіка: виключити якщо type АБО status в exclude списках
            if space_type in exclude_types or space_status in exclude_statuses:
                excluded_count += 1
                continue
            
            filtered.append(space)
        
        logger.info(f"Filtered spaces: kept {len(filtered)}, excluded {excluded_count}")
        return filtered
    
    async def get_spaces_meta(self) -> Dict[str, List[str]]:
        """
        Отримати метадані про простори: унікальні типи та статуси.
        
        Returns:
            {
                "available_types": [...],
                "available_statuses": [...]
            }
        """
        logger.info("Fetching spaces metadata")
        
        try:
            all_spaces = await self.get_all_spaces()
            
            # Зібрати унікальні типи та статуси
            types = set()
            statuses = set()
            
            for space in all_spaces:
                space_type = space.get("type")
                space_status = space.get("status")
                
                if space_type:
                    types.add(space_type)
                if space_status:
                    statuses.add(space_status)
            
            result = {
                "available_types": sorted(list(types)),
                "available_statuses": sorted(list(statuses))
            }
            
            logger.info(
                f"Spaces metadata: {len(result['available_types'])} types, "
                f"{len(result['available_statuses'])} statuses"
            )
            return result
            
        except Exception as e:
            logger.error(f"Error getting spaces metadata: {e}")
            raise
    
    async def get_spaces(
        self,
        query: str = None,
        accessible_only: bool = True,
        start: int = 0,
        limit: int = 25,
        exclude_types: Optional[List[str]] = None,
        exclude_statuses: Optional[List[str]] = None,
        name_contains: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Отримати список просторів Confluence з фільтрацією.
        
        ВАЖЛИВО: Якщо застосовані фільтри (exclude_types/exclude_statuses/name_contains),
        метод автоматично завантажує додаткові сторінки щоб набрати потрібну
        кількість відфільтрованих просторів.
        
        Args:
            query: Пошуковий запит (None = всі простори)
            accessible_only: Тільки доступні простори
            start: Початковий індекс для пагінації (ігнорується при фільтрації)
            limit: Максимальна кількість результатів
            exclude_types: Типи просторів для виключення
            exclude_statuses: Статуси просторів для виключення
            name_contains: Підрядок для пошуку в назві простору (без урахування регістру)
            
        Returns:
            {
                "spaces": [...],
                "start": int,
                "limit": int,
                "size": int,  # Кількість відфільтрованих просторів
                "total": int
            }
        """
        logger.info(
            f"Getting spaces: query={query}, start={start}, limit={limit}, "
            f"exclude_types={exclude_types}, exclude_statuses={exclude_statuses}, name_contains={name_contains}"
        )
        
        try:
            has_filters = (
                (exclude_types and len(exclude_types) > 0) or 
                (exclude_statuses and len(exclude_statuses) > 0) or
                name_contains is not None
            )
            
            if not has_filters:
                # Без фільтрів - просто повернути одну сторінку
                data = await self.confluence.get_spaces(
                    query=query,
                    accessible_only=accessible_only,
                    start=start,
                    limit=limit
                )
                
                spaces = []
                for space_data in data.get("results", []):
                    spaces.append({
                        "id": space_data.get("id"),
                        "key": space_data.get("key"),
                        "name": space_data.get("name"),
                        "type": space_data.get("type"),
                        "status": space_data.get("status", "current")
                    })
                
                result = {
                    "spaces": spaces,
                    "start": data.get("start", start),
                    "limit": data.get("limit", limit),
                    "size": len(spaces),
                    "total": data.get("size", len(spaces))
                }
                
                logger.info(f"Successfully retrieved {len(spaces)} spaces (no filters)")
                return result
            
            # З фільтрами - завантажувати сторінки доки не набереться limit
            logger.info(f"Filtering enabled - will fetch multiple pages to get {limit} filtered results")
            
            filtered_spaces = []
            current_start = 0
            page_limit = min(limit * 3, 100)  # Завантажувати більші порції
            max_pages = 10  # Максимум 10 сторінок щоб не завантажувати всі простори
            pages_fetched = 0
            
            while len(filtered_spaces) < limit and pages_fetched < max_pages:
                logger.info(f"Fetching page {pages_fetched + 1}, start={current_start}, limit={page_limit}")
                
                data = await self.confluence.get_spaces(
                    query=query,
                    accessible_only=accessible_only,
                    start=current_start,
                    limit=page_limit
                )
                
                results = data.get("results", [])
                if not results:
                    logger.info("No more spaces available")
                    break
                
                # Трансформувати
                spaces = []
                for space_data in results:
                    spaces.append({
                        "id": space_data.get("id"),
                        "key": space_data.get("key"),
                        "name": space_data.get("name"),
                        "type": space_data.get("type"),
                        "status": space_data.get("status", "current")
                    })
                
                # Застосувати фільтр name_contains перед exclude фільтрами
                if name_contains:
                    name_contains_lower = name_contains.lower()
                    spaces = [
                        s for s in spaces
                        if name_contains_lower in s.get("name", "").lower()
                    ]
                    logger.info(f"After name_contains filter: {len(spaces)} spaces")
                
                # Фільтрувати за exclude_types та exclude_statuses
                page_filtered = self.filter_spaces(
                    spaces,
                    exclude_types=exclude_types,
                    exclude_statuses=exclude_statuses
                )
                
                filtered_spaces.extend(page_filtered)
                logger.info(f"Page {pages_fetched + 1}: got {len(results)} spaces, after filter: {len(page_filtered)}, total filtered: {len(filtered_spaces)}")
                
                # Якщо отримали менше ніж page_limit - це остання сторінка
                if len(results) < page_limit:
                    logger.info("Reached last page")
                    break
                
                current_start += page_limit
                pages_fetched += 1
            
            # Обрізати до потрібного ліміту
            final_spaces = filtered_spaces[:limit]
            
            result = {
                "spaces": final_spaces,
                "start": 0,  # При фільтрації завжди починаємо з 0
                "limit": limit,
                "size": len(final_spaces),
                "total": len(filtered_spaces)  # Загальна кількість відфільтрованих
            }
            
            logger.info(f"Successfully retrieved {len(final_spaces)} filtered spaces (fetched {pages_fetched} pages)")
            return result
            
        except Exception as e:
            logger.error(f"Error getting spaces: {e}")
            raise
    
    async def get_space_pages(
        self,
        space_key: str,
        expand: str = "body.storage,version"
    ) -> List[Dict[str, Any]]:
        """
        Отримати всі сторінки у просторі.
        
        Args:
            space_key: Ключ простору Confluence
            expand: Поля для розширення
            
        Returns:
            Список об'єктів сторінок
        """
        logger.info(f"Getting all pages from space {space_key}")
        
        try:
            pages = await self.confluence.get_pages_in_space(space_key, expand=expand)
            logger.info(f"Successfully retrieved {len(pages)} pages from space {space_key}")
            return pages
        except Exception as e:
            logger.error(f"Error getting pages from space {space_key}: {e}")
            raise
