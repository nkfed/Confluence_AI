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
import os
from pathlib import Path
from typing import List, Set, Dict, Optional, Any
from src.core.logging.logger import get_logger
from fastapi import HTTPException

logger = get_logger(__name__)


class WhitelistManager:
    """
    Керує whitelist конфігурацією для tag-space операцій.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Ініціалізація WhitelistManager.

        Args:
            config_path: Шлях до JSON конфігурації. Якщо не передано, використовує
                WHITELIST_CONFIG_PATH з env або дефолтний шлях.
        """
        env_path = os.getenv("WHITELIST_CONFIG_PATH")
        effective_path = Path(config_path) if config_path else Path(env_path) if env_path else Path("src/core/whitelist/whitelist_config.json")
        self.config_path = effective_path
        logger.info(f"[WHITELIST] Loading config from: {self.config_path}")
        self.config = self._load_config()
        self._allowed_ids_cache: Dict[str, Set[int]] = {}
        
        # Валідація при ініціалізації
        warnings = self.validate()
        if warnings:
            for warning in warnings:
                logger.warning(f"[WhitelistManager] {warning}")
    
    def _normalize_id(self, value):
        """
        Нормалізує ID: конвертує всі ID до рядків.
        """
        if value is not None:
            return str(value)
        return value

    def _load_config(self) -> dict:
        """
        Load and validate the whitelist configuration from JSON file.
        """
        try:
            logger.info(f"[WHITELIST] Reading configuration file: {self.config_path}")
            with open(self.config_path, 'r', encoding='utf-8') as f:
                raw = json.load(f)

            # Validate and normalize the configuration
            self._validate_and_normalize_config(raw)

            logger.info(f"[WhitelistManager] Loaded configuration from {self.config_path}")
            return raw
        except FileNotFoundError:
            logger.error(f"[WHITELIST] File not found: {self.config_path}")
            raise HTTPException(status_code=400, detail="Whitelist configuration file not found")
        except json.JSONDecodeError as e:
            logger.error(f"[WhitelistManager] Invalid JSON in configuration: {e}")
            raise HTTPException(status_code=400, detail="Invalid whitelist configuration JSON")

    def _validate_and_normalize_config(self, config: dict):
        """
        Validate and normalize the whitelist configuration.
        """
        if "spaces" not in config or not isinstance(config["spaces"], list):
            raise HTTPException(status_code=400, detail="Invalid whitelist structure: 'spaces' key missing or not a list")

        for space in config["spaces"]:
            if not isinstance(space.get("space_key"), str):
                raise HTTPException(status_code=400, detail="Invalid space: 'space_key' must be a string")
            if "pages" not in space or not isinstance(space["pages"], list):
                raise HTTPException(status_code=400, detail=f"Space {space.get('space_key')}: 'pages' must be a list")
            if "description" in space and not isinstance(space["description"], str):
                raise HTTPException(status_code=400, detail=f"Space {space.get('space_key')}: 'description' must be a string if present")

            for page in space["pages"]:
                if not isinstance(page.get("id"), (str, int)) or not str(page["id"]).isdigit():
                    raise HTTPException(status_code=400, detail=f"Space {space.get('space_key')}: Page ID must be an integer or string of digits")
                page["id"] = int(page["id"])  # Normalize to int

                if not isinstance(page.get("name"), str):
                    raise HTTPException(status_code=400, detail=f"Space {space.get('space_key')}: Page name must be a string")

                if "root" in page and not isinstance(page["root"], bool):
                    raise HTTPException(status_code=400, detail=f"Space {space.get('space_key')}: 'root' must be a boolean if present")

                if "children" in page:
                    if not isinstance(page["children"], list):
                        raise HTTPException(status_code=400, detail=f"Space {space.get('space_key')}: 'children' must be a list if present")
                    page["children"] = [
                        int(child) if isinstance(child, (str, int)) and str(child).isdigit() else None
                        for child in page["children"]
                    ]
                    if None in page["children"]:
                        raise HTTPException(status_code=400, detail=f"Space {space.get('space_key')}: Invalid child ID in 'children'")

            # Validate root
            root_pages = [page for page in space["pages"] if page.get("root", False)]
            if len(root_pages) > 1:
                raise HTTPException(status_code=400, detail=f"Space {space.get('space_key')}: Multiple root pages defined")
            if root_pages and root_pages[0]["id"] not in [page["id"] for page in space["pages"]]:
                raise HTTPException(status_code=400, detail=f"Space {space.get('space_key')}: Root page ID does not exist in pages")
    
    def validate(self) -> List[str]:
        """
        Валідує конфігурацію whitelist.
        
        Перевіряє:
        - Не більше одного root=true на space_key
        - Всі id — рядки з цифр або int після нормалізації
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
            
            # Перевірка page IDs перед нормалізацією
            for page in pages:
                page_id = page.get("id")
                if not isinstance(page_id, (str, int)) or (isinstance(page_id, str) and not page_id.isdigit()):
                    warnings.append(
                        f"Space {space_key}: page id {page_id} is invalid (must be a string of digits or an integer)"
                    )

        if not warnings:
            logger.info("[WhitelistManager] Configuration validation passed")
        else:
            for warning in warnings:
                logger.warning(f"[WhitelistManager] {warning}")
        
        return warnings
    
    def get_entry_points(self, space_key: str) -> Set[int]:
        """
        Повертає список whitelist-сторінок (entry points) для простору.
        
        Args:
            space_key: Ключ простору Confluence
            
        Returns:
            Список ID сторінок
        """
        for space in self.config.get("spaces", []):
            if space.get("space_key") == space_key:
                pages = space.get("pages", [])

                # Ensure all pages are dicts with valid structure
                page_map = {
                    int(page["id"]): {
                        "id": int(page["id"]),
                        "name": page.get("name", ""),
                        "children": [int(child) for child in page.get("children", [])]
                    }
                    for page in pages if isinstance(page, dict) and "id" in page
                }

                # Check for root pages
                root_pages = {page_id for page_id, page in page_map.items() if page.get("root", False)}
                if root_pages:
                    return root_pages

                # Find pages that are not children of any other page
                all_children = {child_id for page in page_map.values() for child_id in page.get("children", [])}
                entry_points = set(page_map.keys()) - all_children

                return entry_points

        return set()

    async def get_allowed_ids(self, space_key: str, confluence_client) -> Set[int]:
        """
        Повертає всі дозволені ID для простору, включаючи дочірні сторінки.
        
        Args:
            space_key: Ключ простору Confluence
            client: Клієнт для отримання дочірніх сторінок
        
        Returns:
            Набір дозволених ID (int)
        """
        entry_points = self.get_entry_points(space_key)
        allowed_ids = set()
        visited = set()
        cache = {}

        for entry_id in entry_points:
            allowed_ids.add(int(entry_id))
            logger.info(f"[WhitelistManager] Processing entry point: {entry_id}")

            # Рекурсивно додаємо дочірні сторінки
            try:
                children = await self._get_all_children(int(entry_id), confluence_client, visited, cache)
                allowed_ids.update(children)
            except Exception as e:
                logger.debug(f"[WhitelistManager] No children or error for {entry_id}: {e}")

        # Ensure all IDs are integers before returning
        return {int(x) for x in allowed_ids}
    
    async def _get_all_children(
        self, 
        parent_id: int, 
        client, 
        visited: Set[int], 
        cache: Dict[int, List[int]]
    ) -> Set[int]:
        """
        Рекурсивно отримує всі дочірні сторінки для заданого ID з кешуванням.

        Args:
            parent_id: ID батьківської сторінки
            client: Клієнт для отримання дочірніх сторінок
            visited: Набір вже відвіданих ID для уникнення циклів
            cache: Кеш для збереження результатів викликів get_child_pages

        Returns:
            Набір всіх дочірніх ID
        """
        if visited is None:
            visited = set()
        if parent_id in visited:
            return set()

        visited.add(parent_id)

        if parent_id in cache:
            children = cache[parent_id]
        else:
            children = await client.get_child_pages(parent_id)
            cache[parent_id] = [int(child) for child in children if isinstance(child, (str, int)) and str(child).isdigit()]

        all_children = set(children)
        for child_id in children:
            if child_id not in visited:
                all_children.update(await self._get_all_children(child_id, client, visited, cache))

        return all_children

    def build_page_tree(self, space_key: str) -> List[Dict[str, Any]]:
        """
        Будує деревоподібну структуру сторінок для заданого простору.
        """
        for space in self.config.get("spaces", []):
            if space.get("space_key") == space_key:
                pages = space.get("pages", [])

                # Ensure all pages are dicts with valid structure
                page_map = {
                    int(page["id"]): {
                        "id": int(page["id"]),
                        "name": page.get("name", ""),
                        "children": [int(child) for child in page.get("children", [])]
                    }
                    for page in pages if isinstance(page, dict) and "id" in page
                }

                def build_tree(node_id: int) -> Dict[str, Any]:
                    node = page_map[node_id]
                    return {
                        "id": node["id"],
                        "name": node["name"],
                        "children": [build_tree(child_id) for child_id in node.get("children", [])]
                    }

                entry_points = self.get_entry_points(space_key)
                return [build_tree(entry_id) for entry_id in entry_points]

        return []

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
