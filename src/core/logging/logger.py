"""
Centralized logging module.

All loggers are configured through logging_config.py with proper rotation.
This module provides a unified interface to get loggers by name.
"""

import logging
from typing import Optional

from src.core.logging.logging_config import configure_logging

_configured = False


def _ensure_configured() -> None:
    """Ensure logging is configured before first use."""
    global _configured
    if not _configured:
        configure_logging()
        _configured = True


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Get a logger by name with centralized configuration.

    Loggers are routed based on their name prefix:
    - api.* → "api" logger (api.log)
    - agents.* → "agents" logger (agents.log)
    - services.* → "services" logger (services.log)
    - clients.* → "clients" logger (clients.log)
    - utils.* → "utils" logger (utils.log)
    - ai.* / core.ai → "ai" logger (ai_calls.log)
    - ai_router → "ai_router" logger (ai_router.log)
    - security / policy → "security" logger (security.log)
    - audit → "audit" logger (audit.log)
    - metrics → "metrics" logger (metrics.log)
    
    All loggers use RotatingFileHandler with automatic rotation when size exceeds limit.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        logging.Logger: Configured logger instance
    """
    _ensure_configured()

    if not name:
        return logging.getLogger("app")

    # Map component names to root logger names
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
    if "metrics" in name:
        return logging.getLogger("metrics")

    return logging.getLogger(name)


# ===================================================================
# Convenience exports for backward compatibility
# Use get_logger() instead, but these are available for direct access
# ===================================================================

def _get_exported_logger(name: str) -> logging.Logger:
    """Get logger and ensure it's configured."""
    _ensure_configured()
    return logging.getLogger(name)


# Pre-configured loggers for common use cases
security_logger = None
audit_logger = None


def _initialize_exported_loggers() -> None:
    """Initialize exported logger references."""
    global security_logger, audit_logger
    _ensure_configured()
    security_logger = logging.getLogger("security")
    audit_logger = logging.getLogger("audit")


# Initialize on module load
_initialize_exported_loggers()

__all__ = ["get_logger", "security_logger", "audit_logger"]
