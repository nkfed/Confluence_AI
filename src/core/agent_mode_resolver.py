"""
AgentModeResolver — централізований механізм визначення режиму роботи агентів.

Підтримувані режими:
- TEST:
    • Абсолютно безпечний режим.
    • Заборонено будь-які зміни у Confluence.
    • Дозволено працювати лише з whitelist сторінок.
    • Агент повинен працювати у dry-run режимі.

- SAFE_TEST:
    • Напів-безпечний режим.
    • Дозволено оновлювати ТІЛЬКИ whitelist сторінок.
    • Заборонено оновлювати будь-які інші сторінки.
    • Використовується для інтеграційних тестів та staging.

- PROD:
    • Повний доступ.
    • Агент може оновлювати будь-які сторінки.
"""

import os
from typing import List
from settings import AgentMode


class AgentModeResolver:
    """Централізований резолвер для режимів агентів та whitelist."""
    
    @staticmethod
    def resolve_mode(agent_name: str, explicit_mode: str = None) -> str:
        """
        Визначає режим роботи агента з пріоритетом:
        1. Explicit override (параметр)
        2. Per-agent override з .env (e.g., SUMMARY_AGENT_MODE)
        3. Global mode з .env (AGENT_MODE)
        4. Default: TEST
        
        Args:
            agent_name: Назва агента (e.g., "SUMMARY_AGENT")
            explicit_mode: Явне перевизначення режиму
            
        Returns:
            Режим роботи: TEST, SAFE_TEST, або PROD
        """
        # 1. Explicit override has highest priority
        if explicit_mode:
            return explicit_mode
        
        # 2. Per-agent override (e.g., SUMMARY_AGENT_MODE)
        specific_key = f"{agent_name}_MODE"
        specific_mode = os.getenv(specific_key)
        if specific_mode:
            return specific_mode
        
        # 3. Global mode
        global_mode = os.getenv("AGENT_MODE", AgentMode.TEST)
        return global_mode
    
    @staticmethod
    def resolve_whitelist(agent_name: str) -> List[str]:
        """
        Завантажує whitelist сторінок для агента з .env.
        
        Args:
            agent_name: Назва агента (e.g., "SUMMARY_AGENT")
            
        Returns:
            Список ID сторінок з whitelist
        """
        key = f"{agent_name}_TEST_PAGE"
        raw = os.getenv(key)
        
        if not raw:
            return []
        
        return [p.strip() for p in raw.split(",") if p.strip()]
    
    @staticmethod
    def should_perform_dry_run(mode: str) -> bool:
        """
        Визначає, чи потрібен dry-run режим.
        
        Args:
            mode: Режим роботи агента
            
        Returns:
            True якщо режим TEST (сухий прогін без змін)
        """
        return mode == AgentMode.TEST
    
    @staticmethod
    def can_modify_confluence(mode: str, page_id: str, whitelist: List[str]) -> bool:
        """
        Перевіряє, чи може агент змінювати Confluence.
        
        Args:
            mode: Режим роботи
            page_id: ID сторінки
            whitelist: Список дозволених сторінок
            
        Returns:
            True якщо зміни дозволені
        """
        if mode == AgentMode.PROD:
            return True
        
        if mode == AgentMode.SAFE_TEST:
            return page_id in whitelist
        
        if mode == AgentMode.TEST:
            return False  # Dry-run only, no actual changes
        
        return False
    
    @staticmethod
    def is_valid_root_page(mode: str, root_page_id: str, allowed_root_ids: List[str]) -> bool:
        """
        Перевіряє, чи дозволений root_page_id для /bulk/tag-tree у поточному режимі.
        
        Режимна логіка:
        - PROD: дозволені ВСІ root_page_id (повний доступ)
        - SAFE_TEST: дозволені ТІЛЬКИ root_page_id з whitelist
        - TEST: дозволені ТІЛЬКИ root_page_id з whitelist (dry-run)
        
        Args:
            mode: Режим роботи агента (TEST, SAFE_TEST, PROD)
            root_page_id: ID кореневої сторінки дерева
            allowed_root_ids: Список дозволених root page IDs з whitelist
            
        Returns:
            True якщо root_page_id дозволений у поточному режимі
        """
        if mode == AgentMode.PROD:
            return True  # ✅ PROD mode: all root pages allowed
        
        # TEST and SAFE_TEST: only whitelisted roots
        return root_page_id in allowed_root_ids

