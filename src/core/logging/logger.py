import logging
from typing import Optional
import os
from logging.handlers import RotatingFileHandler

from src.core.logging.logging_config import configure_logging

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

# Форматування
formatter = logging.Formatter(
    "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# --- SECURITY LOGGER ---
security_logger = logging.getLogger("security")
security_logger.setLevel(logging.WARNING)
security_handler = RotatingFileHandler(
    os.path.join(LOG_DIR, "security.log"), maxBytes=5_000_000, backupCount=5, encoding="utf-8"
)
security_handler.setFormatter(formatter)
security_logger.addHandler(security_handler)

# --- AUDIT LOGGER ---
audit_logger = logging.getLogger("audit")
audit_logger.setLevel(logging.INFO)
audit_handler = RotatingFileHandler(
    os.path.join(LOG_DIR, "audit.log"), maxBytes=10_000_000, backupCount=10, encoding="utf-8"
)
audit_handler.setFormatter(formatter)
audit_logger.addHandler(audit_handler)

# --- AI LOGGER ---
ai_logger = logging.getLogger("ai")
ai_logger.setLevel(logging.INFO)
ai_handler = RotatingFileHandler(
    os.path.join(LOG_DIR, "ai_calls.log"),
    maxBytes=10_000_000,
    backupCount=10,
    encoding="utf-8"
)
ai_handler.setFormatter(formatter)
ai_logger.addHandler(ai_handler)

# --- AI ROUTER LOGGER ---
ai_router_logger = logging.getLogger("ai_router")
ai_router_logger.setLevel(logging.INFO)
ai_router_handler = RotatingFileHandler(
    os.path.join(LOG_DIR, "ai_router.log"),
    maxBytes=5_000_000,
    backupCount=5,
    encoding="utf-8"
)
ai_router_handler.setFormatter(formatter)
ai_router_logger.addHandler(ai_router_handler)

_configured = False


def _ensure_configured() -> None:
    global _configured
    if not _configured:
        configure_logging()
        _configured = True


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Повертає логер з централізованою конфігурацією.
    Якщо name починається з відомого префіксу (api., agents., services., clients., utils.),
    відповідний логер буде маршрутизований у свій файл.
    """
    _ensure_configured()

    if not name:
        return logging.getLogger("app")

    # Нормалізуємо ім'я до кореневого логера компонента
    if name.startswith("api.") or name.startswith("src.api."):
        return logging.getLogger("api")
    if name.startswith("agents.") or name.startswith("src.agents."):
        return logging.getLogger("agents")
    if name.startswith("services.") or name.startswith("src.services."):
        return logging.getLogger("services")
    if name.startswith("clients.") or name.startswith("src.clients."):
        return logging.getLogger("clients")
    if name.startswith("utils.") or name.startswith("src.utils."):
        return logging.getLogger("utils")
    if name.startswith("ai.") or "core.ai" in name:
        return logging.getLogger("ai")
    if name.startswith("ai_router") or "ai_router" in name:
        return logging.getLogger("ai_router")
    if "policy" in name or "security" in name:
        return logging.getLogger("security")
    if "audit" in name:
        return logging.getLogger("audit")

    return logging.getLogger(name)
