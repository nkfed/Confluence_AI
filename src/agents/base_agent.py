import os
from abc import ABC, abstractmethod
from settings import settings, AgentMode
from src.core.logging.logger import get_logger, security_logger, audit_logger

logger = get_logger(__name__)

class BaseAgent(ABC):
    """
    Базовий агент, який може бути розширений.
    """

    def __init__(self, mode: str = None):
        self.mode = mode or settings.AGENT_MODE
        self.allowed_test_page_id = "19713687690"
        audit_logger.info(f"Agent initialized mode={self.mode}")

    def is_page_allowed(self, page_id: str) -> bool:
        """
        Перевірка, чи дозволено змінювати сторінку.
        """
        if self.mode == AgentMode.PROD:
            return True
        return page_id == self.allowed_test_page_id

    def enforce_page_policy(self, page_id: str):
        """
        Якщо сторінка не дозволена — логувати і зупинити.
        """
        if not self.is_page_allowed(page_id):
            security_logger.warning(
                f"POLICY VIOLATION: Attempt to modify forbidden page_id={page_id} in mode={self.mode}"
            )
            audit_logger.warning(
                f"action=update_page page_id={page_id} mode={self.mode} status=denied"
            )
            raise PermissionError(f"Modifying page {page_id} is forbidden in test_mode")

        audit_logger.info(
            f"action=update_page page_id={page_id} mode={self.mode} status=allowed"
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