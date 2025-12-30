import os
from abc import ABC, abstractmethod
from settings import settings, AgentMode
from src.core.logging.logger import get_logger, security_logger, audit_logger
from src.core.agent_mode_resolver import AgentModeResolver

logger = get_logger(__name__)

class BaseAgent(ABC):
    """
    Базовий агент з уніфікованою логікою режимів.
    
    Підтримувані режими:
    - TEST: dry-run, жодних змін у Confluence
    - SAFE_TEST: зміни тільки whitelist сторінок
    - PROD: повний доступ
    """

    def __init__(self, agent_name: str = "AGENT", mode: str = None):
        """
        Initialize agent with centralized mode resolution.
        
        Args:
            agent_name: Agent name in uppercase (e.g., "SUMMARY_AGENT")
            mode: Explicit mode override (TEST, SAFE_TEST, or PROD)
        """
        self.agent_name = agent_name
        
        # Centralized mode resolution
        self.mode = AgentModeResolver.resolve_mode(agent_name, explicit_mode=mode)
        
        # Centralized whitelist resolution
        self.allowed_test_pages = AgentModeResolver.resolve_whitelist(agent_name)
        
        audit_logger.info(
            f"{agent_name} initialized mode={self.mode} "
            f"(via AgentModeResolver) "
            f"allowed_test_pages={len(self.allowed_test_pages)}"
        )

    def is_dry_run(self) -> bool:
        """
        Перевірка, чи агент працює у dry-run режимі.
        
        Returns:
            True якщо режим TEST (без змін у Confluence)
        """
        return AgentModeResolver.should_perform_dry_run(self.mode)

    def is_page_allowed(self, page_id: str) -> bool:
        """
        Unified logic for TEST / SAFE_TEST / PROD:

        TEST:
            - No updates allowed anywhere.
            - Only whitelist pages allowed for read-only operations.

        SAFE_TEST:
            - Updates allowed ONLY for whitelist pages.
            - All other pages are blocked.

        PROD:
            - Full access to all pages.
            
        Args:
            page_id: Confluence page ID
            
        Returns:
            True if page access/modification is allowed
        """
        if self.mode == AgentMode.PROD:
            return True
        
        if self.mode == AgentMode.SAFE_TEST:
            return page_id in self.allowed_test_pages
        
        if self.mode == AgentMode.TEST:
            return page_id in self.allowed_test_pages
        
        return False

    def enforce_page_policy(self, page_id: str, allowed_pages: list = None):
        """
        Enforce page MODIFICATION policy using AgentModeResolver.
        
        - PROD mode: allows all pages
        - SAFE_TEST mode: allows only whitelisted pages
        - TEST mode: blocks all modifications (dry-run only)
        
        Args:
            page_id: Confluence page ID
            allowed_pages: Optional list of allowed page IDs (overrides self.allowed_test_pages)
            
        Raises:
            PermissionError: If page MODIFICATION is not allowed
        """
        # ✅ Використовуємо переданий список або внутрішній
        effective_allowed_pages = allowed_pages if allowed_pages is not None else self.allowed_test_pages
        
        logger.debug(
            f"[BaseAgent] enforce_page_policy: page_id={page_id}, mode={self.mode}, "
            f"allowed_pages={effective_allowed_pages[:5] if effective_allowed_pages else []}"
        )
        
        # Use AgentModeResolver for proper policy check
        if not AgentModeResolver.can_modify_confluence(self.mode, page_id, effective_allowed_pages):
            security_logger.warning(
                f"POLICY VIOLATION: Attempt to modify forbidden page_id={page_id} "
                f"in mode={self.mode}"
            )
            audit_logger.warning(
                f"action=modify_page page_id={page_id} mode={self.mode} "
                f"status=denied allowed_pages={effective_allowed_pages}"
            )
            raise PermissionError(
                f"Modifying page {page_id} is forbidden in {self.mode} mode. "
                f"Allowed in PROD (all) or SAFE_TEST (whitelist: {effective_allowed_pages})"
            )

        audit_logger.info(
            f"action=modify_page page_id={page_id} mode={self.mode} status=allowed"
        )
    
    def enforce_root_policy(self, root_page_id: str):
        """
        Enforce root page policy for /bulk/tag-tree operations.
        
        Режимна логіка:
        - PROD: дозволені ВСІ root_page_id
        - SAFE_TEST: дозволені ТІЛЬКИ whitelist root_page_id
        - TEST: дозволені ТІЛЬКИ whitelist root_page_id (dry-run)
        
        Args:
            root_page_id: ID кореневої сторінки дерева
            
        Raises:
            PermissionError: Якщо root_page_id не дозволений у поточному режимі
        """
        if not AgentModeResolver.is_valid_root_page(
            self.mode, 
            root_page_id, 
            self.allowed_test_pages
        ):
            security_logger.warning(
                f"POLICY VIOLATION: Attempt to process root page_id={root_page_id} "
                f"in mode={self.mode} (not in whitelist)"
            )
            audit_logger.warning(
                f"action=tag_tree root_page_id={root_page_id} mode={self.mode} "
                f"status=denied allowed_roots={self.allowed_test_pages}"
            )
            raise PermissionError(
                f"Root page {root_page_id} is not allowed in {self.mode} mode. "
                f"Allowed in PROD (all pages) or TEST/SAFE_TEST (whitelist: {self.allowed_test_pages})"
            )
        
        audit_logger.info(
            f"action=tag_tree root_page_id={root_page_id} mode={self.mode} status=allowed"
        )

    def write_guidelines(self, content: str):
        """
        Створити guidelines.md у UTF‑8.
        """
        os.makedirs(".junie", exist_ok=True)
        path = ".junie/guidelines.md"
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            logger.info(f"Guidelines written to {path} in UTF-8")
        except Exception as e:
            logger.error(f"Failed to write guidelines: {e}")
            raise

    @abstractmethod
    def process_page(self, page_id: str):
        """Базовий метод, який мають реалізувати всі агенти."""
        pass