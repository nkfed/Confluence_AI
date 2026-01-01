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
from src.core.whitelist.whitelist_manager import WhitelistManager


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
        Завантажує whitelist сторінок лише з whitelist_config.json через WhitelistManager.
        Env-перемінні та хардкоди не використовуються.
        Повертає об'єднаний список усіх дозволених сторінок (у форматі str) по всіх просторах.
        """
        from src.core.logging.logger import get_logger
        logger = get_logger(__name__)

        try:
            manager = WhitelistManager()
            all_ids: set[int] = set()
            # Об'єднуємо явні id (entry points) з конфігурації для всіх просторів
            for space in manager.config.get("spaces", []):
                pages = space.get("pages", []) or []
                explicit_ids = {int(page.get("id")) for page in pages if page.get("id")}
                all_ids.update(explicit_ids)

            page_ids = [str(pid) for pid in all_ids]
            logger.info(
                f"[WHITELIST] Loaded from whitelist_config.json for agent={agent_name}: {len(page_ids)} entries"
            )
            return page_ids
        except Exception as e:
            logger.error(f"[AgentModeResolver] Failed to load whitelist via WhitelistManager: {e}")
            return []
    
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
        from src.core.logging.logger import get_logger
        logger = get_logger(__name__)
        
        if mode == AgentMode.PROD:
            logger.debug(f"[AgentModeResolver] PROD mode - allowing page {page_id}")
            return True
        
        if mode == AgentMode.SAFE_TEST:
            # ✅ Конвертуємо page_id в int для порівняння
            try:
                page_id_int = int(page_id)
            except (ValueError, TypeError):
                logger.error(f"[AgentModeResolver] Invalid page_id: {page_id}")
                return False
            
            # ✅ Конвертуємо whitelist в int якщо потрібно
            whitelist_ints = []
            for item in whitelist:
                try:
                    if isinstance(item, int):
                        whitelist_ints.append(item)
                    else:
                        whitelist_ints.append(int(item))
                except (ValueError, TypeError):
                    logger.warning(f"[AgentModeResolver] Skipping invalid whitelist item: {item}")
            
            result = page_id_int in whitelist_ints
            logger.info(
                f"[AgentModeResolver] SAFE_TEST mode - page_id={page_id_int}, "
                f"whitelist={whitelist_ints[:10]}, allowed={result}"
            )
            return result
        
        if mode == AgentMode.TEST:
            logger.debug(f"[AgentModeResolver] TEST mode - blocking page {page_id} (dry-run only)")
            return False  # Dry-run only, no actual changes
        
        logger.warning(f"[AgentModeResolver] Unknown mode '{mode}' - blocking page {page_id}")
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

