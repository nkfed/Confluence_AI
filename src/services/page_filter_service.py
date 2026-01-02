"""
PageFilterService — сервіс для фільтрації сторінок Confluence.

Підтримує:
- Виключення архівованих сторінок
- Виключення індексних сторінок
- Виключення шаблонів
- Виключення порожніх сторінок
- Фільтрація за регулярним виразом title
- SAFE_TEST whitelist
"""

import re
from typing import Dict, Any, List, Optional
from src.core.logging.logger import get_logger
from src.core.agent_mode_resolver import AgentModeResolver

logger = get_logger(__name__)


class PageFilterService:
    """Сервіс для фільтрації сторінок згідно з заданими критеріями."""
    
    def __init__(self, whitelist: List[str] = None):
        """
        Ініціалізація сервісу фільтрації.
        
        Args:
            whitelist: Список ID сторінок, дозволених для SAFE_TEST режиму
        """
        self.whitelist = whitelist or []
    
    def is_archived(self, page: Dict[str, Any]) -> bool:
        """
        Перевіряє, чи є сторінка архівованою.
        
        Args:
            page: Об'єкт сторінки Confluence
            
        Returns:
            True якщо сторінка архівована
        """
        status = page.get("status", "").lower()
        is_arch = status == "archived"
        
        if is_arch:
            logger.debug(f"Page {page.get('id')} is archived")
        
        return is_arch
    
    def is_index_page(self, page: Dict[str, Any]) -> bool:
        """
        Перевіряє, чи є сторінка індексною.
        
        Критерії:
        - Назва містить "Index" або "index"
        - Назва містить "Contents" або "Table of Contents"
        
        Args:
            page: Об'єкт сторінки Confluence
            
        Returns:
            True якщо сторінка є індексною
        """
        title = page.get("title", "").lower()
        
        index_patterns = [
            "index",
            "table of contents",
            "contents",
            "зміст",
            "перелік"
        ]
        
        is_idx = any(pattern in title for pattern in index_patterns)
        
        if is_idx:
            logger.debug(f"Page {page.get('id')} '{page.get('title')}' is an index page")
        
        return is_idx
    
    def is_template(self, page: Dict[str, Any]) -> bool:
        """
        Перевіряє, чи є сторінка шаблоном.
        
        Критерії:
        - Тип сторінки = "template"
        - Назва містить "Template" або "template"
        
        Args:
            page: Об'єкт сторінки Confluence
            
        Returns:
            True якщо сторінка є шаблоном
        """
        page_type = page.get("type", "").lower()
        title = page.get("title", "").lower()
        
        is_tmpl = page_type == "template" or "template" in title or "шаблон" in title
        
        if is_tmpl:
            logger.debug(f"Page {page.get('id')} '{page.get('title')}' is a template")
        
        return is_tmpl
    
    def is_empty(self, page: Dict[str, Any]) -> bool:
        """
        Перевіряє, чи є сторінка порожньою.
        
        Критерії:
        - Немає body.storage.value
        - body.storage.value має менше ніж 50 символів (без HTML тегів)
        
        Args:
            page: Об'єкт сторінки Confluence (з розширенням body.storage)
            
        Returns:
            True якщо сторінка порожня
        """
        try:
            body = page.get("body")

            # Якщо body відсутній — вважаємо, що сторінка не порожня (може бути неповна відповідь API)
            if not body or "storage" not in body:
                return False

            content = body.get("storage", {}).get("value", "") or ""

            # Видалити HTML теги для підрахунку
            plain_text = re.sub(r"<[^>]+>", "", content).strip()

            # Вважаємо сторінку пустою лише якщо реального тексту < 5 символів
            is_empt = len(plain_text) < 5

            if is_empt:
                logger.debug(f"Page {page.get('id')} '{page.get('title')}' is empty ({len(plain_text)} chars)")

            return is_empt
        except Exception as e:
            logger.warning(f"Error checking if page {page.get('id')} is empty: {e}")
            return False
    
    def matches_title_regex(self, page: Dict[str, Any], regex_pattern: Optional[str]) -> bool:
        """
        Перевіряє, чи відповідає назва сторінки регулярному виразу для виключення.
        
        Args:
            page: Об'єкт сторінки Confluence
            regex_pattern: Регулярний вираз для виключення (None = не застосовувати)
            
        Returns:
            True якщо назва НЕ відповідає патерну (сторінка повинна бути виключена)
        """
        if not regex_pattern:
            return False  # Якщо патерн не заданий, не виключаємо
        
        title = page.get("title", "")
        
        try:
            matches = bool(re.search(regex_pattern, title, re.IGNORECASE))
            
            if matches:
                logger.debug(f"Page {page.get('id')} '{title}' matches exclusion regex '{regex_pattern}'")
            
            return matches
        except re.error as e:
            logger.error(f"Invalid regex pattern '{regex_pattern}': {e}")
            return False
    
    def is_allowed_in_safe_test(self, page_id: str) -> bool:
        """
        Перевіряє, чи дозволена сторінка у SAFE_TEST режимі (whitelist).
        
        Args:
            page_id: ID сторінки
            
        Returns:
            True якщо сторінка у whitelist
        """
        page_id_str = str(page_id)
        is_allowed = page_id_str in {str(pid) for pid in self.whitelist}
        
        if not is_allowed:
            logger.debug(f"Page {page_id} is NOT in SAFE_TEST whitelist")
        
        return is_allowed
    
    def should_exclude_page(
        self,
        page: Dict[str, Any],
        mode: str,
        exclude_archived: bool = True,
        exclude_index_pages: bool = True,
        exclude_templates: bool = True,
        exclude_empty_pages: bool = True,
        exclude_by_title_regex: Optional[str] = None
    ) -> tuple[bool, Optional[str]]:
        """
        Визначає, чи повинна сторінка бути виключена на основі режиму та критеріїв.
        """
        page_id = page.get("id", "unknown")

        # ---------------------------------------------------------
        # SAFE_TEST whitelist has absolute priority
        # ---------------------------------------------------------
        if mode == "SAFE_TEST":
            # If page IS in whitelist → always allowed (bypass all filters)
            if self.is_allowed_in_safe_test(page_id):
                return False, "allowed"
            
            # If page NOT in whitelist → always excluded
            return True, "whitelist"

        # Check archived pages
        if exclude_archived and self.is_archived(page):
            return True, "Page is archived"

        # Check index pages
        if exclude_index_pages and self.is_index_page(page):
            return True, "Page is an index page"

        # Check templates
        if exclude_templates and self.is_template(page):
            return True, "Page is a template"

        # Check title regex
        if exclude_by_title_regex and self.matches_title_regex(page, exclude_by_title_regex):
            return True, "Page title matches exclusion regex"

        # Check empty pages (last filter)
        if exclude_empty_pages and self.is_empty(page):
            return True, "Page is empty"

        # Check mode-specific logic
        if mode == "TEST":
            if not self.is_allowed_in_safe_test(page_id):
                return True, "not in whitelist"
            return False, "allowed"

        elif mode == "PROD":
            # If no filters matched in PROD → allow, reason=None
            return False, None

        return False, "allowed"
