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
            content = page.get("body", {}).get("storage", {}).get("value", "")
            
            # Видалити HTML теги для підрахунку
            plain_text = re.sub(r"<[^>]+>", "", content).strip()
            
            is_empt = len(plain_text) < 50
            
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
        is_allowed = page_id in self.whitelist
        
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
        Універсальний метод для перевірки, чи повинна сторінка бути виключена.
        
        Args:
            page: Об'єкт сторінки Confluence
            mode: Режим роботи агента (TEST, SAFE_TEST, PROD)
            exclude_archived: Виключити архівовані сторінки
            exclude_index_pages: Виключити індексні сторінки
            exclude_templates: Виключити шаблони
            exclude_empty_pages: Виключити порожні сторінки
            exclude_by_title_regex: Регулярний вираз для виключення за назвою
            
        Returns:
            (should_exclude, reason): True якщо сторінка повинна бути виключена + причина
        """
        page_id = page.get("id", "unknown")
        
        # 1. Перевірка режиму SAFE_TEST whitelist
        if mode == "SAFE_TEST" and not self.is_allowed_in_safe_test(page_id):
            return True, f"Not in SAFE_TEST whitelist"
        
        # 2. Архівовані сторінки
        if exclude_archived and self.is_archived(page):
            return True, "Page is archived"
        
        # 3. Індексні сторінки
        if exclude_index_pages and self.is_index_page(page):
            return True, "Page is an index"
        
        # 4. Шаблони
        if exclude_templates and self.is_template(page):
            return True, "Page is a template"
        
        # 5. Порожні сторінки
        if exclude_empty_pages and self.is_empty(page):
            return True, "Page is empty"
        
        # 6. Regex фільтр
        if exclude_by_title_regex and self.matches_title_regex(page, exclude_by_title_regex):
            return True, f"Title matches exclusion regex"
        
        # Сторінка не виключена
        return False, None
