"""
WhitelistManager — централізований механізм керування whitelist для tag-space.

Особливості:
- Структурований по спейсах
- Root-сторінка необов'язкова, але якщо є — то одна
- Whitelist-сторінки є точками входу
- Кожна точка входу обробляє своє піддерево
- У TEST/SAFE_TEST обробляються тільки whitelist-сторінки
- У PROD whitelist ігнорується
"""

import json
from pathlib import Path
from typing import List, Set, Dict, Optional
from src.core.logging.logger import get_logger

logger = get_logger(__name__)


class WhitelistManager:
    """
    Керує whitelist конфігурацією для tag-space операцій.
    """
    
    def __init__(self, config_path: str = "src/core/whitelist/whitelist_config.json"):
        """
        Ініціалізація WhitelistManager.
        
        Args:
            config_path: Шлях до JSON конфігурації
        """
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self._allowed_ids_cache: Dict[str, Set[int]] = {}
        
        # Валідація при ініціалізації
        warnings = self.validate()
        if warnings:
            for warning in warnings:
                logger.warning(f"[WhitelistManager] {warning}")
    
    def _load_config(self) -> dict:
        """
        Завантажує конфігурацію з JSON файлу.
        
        Returns:
            Словник з конфігурацією
            
        Raises:
            FileNotFoundError: Якщо файл не знайдено
            json.JSONDecodeError: Якщо JSON невалідний
        """
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            logger.info(f"[WhitelistManager] Loaded configuration from {self.config_path}")
            return config
        except FileNotFoundError:
            logger.error(f"[WhitelistManager] Configuration file not found: {self.config_path}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"[WhitelistManager] Invalid JSON in configuration: {e}")
            raise
    
    def validate(self) -> List[str]:
        """
        Валідує конфігурацію whitelist.
        
        Перевіряє:
        - Не більше одного root=true на space_key
        - Всі id — числа
        - Структура валідна
        
        Returns:
            Список warning-повідомлень (порожній якщо все ОК)
        """
        warnings = []
        
        if "spaces" not in self.config:
            warnings.append("Missing 'spaces' key in configuration")
            return warnings
        
        for space in self.config.get("spaces", []):
            space_key = space.get("space_key")
            
            if not space_key:
                warnings.append(f"Space without space_key found")
                continue
            
            pages = space.get("pages", [])
            if not pages:
                warnings.append(f"Space {space_key} has no pages defined")
                continue
            
            # Перевірка root pages
            root_count = sum(1 for page in pages if page.get("root", False))
            if root_count > 1:
                warnings.append(
                    f"Space {space_key} has {root_count} root pages (should be 0 or 1)"
                )
            
            # Перевірка page IDs
            for page in pages:
                page_id = page.get("id")
                if not isinstance(page_id, int):
                    warnings.append(
                        f"Space {space_key}: page id '{page_id}' is not an integer"
                    )
        
        if not warnings:
            logger.info("[WhitelistManager] Configuration validation passed")
        
        return warnings
    
    def get_entry_points(self, space_key: str) -> List[dict]:
        """
        Повертає список whitelist-сторінок (entry points) для простору.
        
        Args:
            space_key: Ключ простору Confluence
            
        Returns:
            Список словників з полями: {"id": int, "name": str, "root": bool}
        """
        for space in self.config.get("spaces", []):
            if space.get("space_key") == space_key:
                pages = space.get("pages", [])
                logger.info(
                    f"[WhitelistManager] Found {len(pages)} entry points for space {space_key}"
                )
                return pages
        
        logger.info(f"[WhitelistManager] No entry points found for space {space_key}")
        return []
    
    async def get_allowed_ids(
        self, 
        space_key: str, 
        confluence_client
    ) -> Set[int]:
        """
        Будує множину дозволених page_id для простору.
        
        Логіка:
        - Для root=true → додає всю піддеревну структуру від root
        - Для root=false → додає сторінку та її дочірні
        - Дублікати автоматично усуваються (Set)
        
        Args:
            space_key: Ключ простору
            confluence_client: Клієнт для отримання дочірніх сторінок
            
        Returns:
            Множина дозволених page_id
        """
        # Кеш для оптимізації
        if space_key in self._allowed_ids_cache:
            logger.debug(f"[WhitelistManager] Using cached allowed_ids for {space_key}")
            return self._allowed_ids_cache[space_key]
        
        entry_points = self.get_entry_points(space_key)
        if not entry_points:
            logger.warning(f"[WhitelistManager] No entry points for {space_key}, returning empty set")
            return set()
        
        logger.info(
            f"[WhitelistManager] Entry points for {space_key}: "
            f"{[{'id': e['id'], 'name': e.get('name'), 'root': e.get('root', False)} for e in entry_points]}"
        )
        
        allowed_ids = set()
        
        for entry in entry_points:
            page_id = entry["id"]
            is_root = entry.get("root", False)
            name = entry.get("name", f"Page {page_id}")
            
            logger.info(
                f"[WhitelistManager] Processing entry point: {name} (id={page_id}, root={is_root})"
            )
            
            # Додаємо саму сторінку
            allowed_ids.add(page_id)
            
            # Отримуємо дочірні сторінки
            try:
                children = await self._get_all_children(page_id, confluence_client)
                allowed_ids.update(children)
                logger.info(
                    f"[WhitelistManager] Entry {page_id} → added {len(children)} descendants. "
                    f"Total collected: {children if len(children) <= 10 else f'{len(children)} IDs'}"
                )
            except Exception as e:
                logger.error(
                    f"[WhitelistManager] Failed to get children for {page_id}: {e}"
                )
        
        logger.info(
            f"[WhitelistManager] Final allowed_ids for {space_key}: {len(allowed_ids)} pages"
        )
        logger.debug(
            f"[WhitelistManager] Allowed IDs (sorted): {sorted(list(allowed_ids))}"
        )
        
        # Кешуємо результат
        self._allowed_ids_cache[space_key] = allowed_ids
        
        return allowed_ids
    
    async def _get_all_children(
        self, 
        page_id: int, 
        confluence_client
    ) -> Set[int]:
        """
        Рекурсивно отримує всі дочірні сторінки.
        
        Args:
            page_id: ID батьківської сторінки
            confluence_client: Клієнт Confluence
            
        Returns:
            Множина ID всіх дочірніх сторінок
        """
        children_ids = set()
        
        try:
            # Отримуємо дочірні сторінки (повертає list[str])
            children = await confluence_client.get_child_pages(str(page_id))
            
            logger.debug(
                f"[WhitelistManager] Page {page_id} has {len(children)} direct children: {children}"
            )
            
            for child_id_str in children:
                child_id = int(child_id_str)
                children_ids.add(child_id)
                
                # Рекурсивно отримуємо дочірні для дочірньої сторінки
                grandchildren = await self._get_all_children(child_id, confluence_client)
                children_ids.update(grandchildren)
                
                if grandchildren:
                    logger.debug(
                        f"[WhitelistManager] Page {child_id} has {len(grandchildren)} descendants"
                    )
        
        except Exception as e:
            logger.debug(f"[WhitelistManager] No children or error for {page_id}: {e}")
        
        return children_ids
    
    def is_allowed(
        self, 
        space_key: str, 
        page_id: int, 
        allowed_ids: Set[int]
    ) -> bool:
        """
        Перевіряє, чи дозволено обробляти сторінку.
        
        Args:
            space_key: Ключ простору
            page_id: ID сторінки
            allowed_ids: Множина дозволених ID
            
        Returns:
            True якщо сторінка дозволена, False інакше
        """
        is_allowed = page_id in allowed_ids
        
        if is_allowed:
            logger.debug(f"[WhitelistManager] Page {page_id} is allowed")
        else:
            logger.info(f"[WhitelistManager] Page {page_id} is NOT in whitelist, skipping")
        
        return is_allowed
    
    def clear_cache(self):
        """Очищає кеш allowed_ids."""
        self._allowed_ids_cache.clear()
        logger.info("[WhitelistManager] Cache cleared")
