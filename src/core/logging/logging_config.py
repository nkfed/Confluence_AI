import logging
import logging.config
import os
from typing import Dict, Any

from settings import settings
from src.core.logging.context import request_id_var


class RequestIdFilter(logging.Filter):
    def filter(self, record):
        record.request_id = request_id_var.get()
        return True


def ensure_log_dir_exists(log_dir: str) -> None:
    if not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)


def get_logging_config() -> Dict[str, Any]:
    log_level = settings.LOG_LEVEL.upper()
    log_dir = settings.LOG_DIR
    use_json = settings.LOG_JSON

    ensure_log_dir_exists(log_dir)

    if use_json:
        formatter_name = "json"
    else:
        formatter_name = "standard"

    return {
        "version": 1,
        "disable_existing_loggers": False,
        "filters": {
            "request_id": {
                "()": "src.core.logging.logging_config.RequestIdFilter",
            }
        },
        "formatters": {
            "standard": {
                "format": "%(asctime)s | %(levelname)s | %(name)s | %(request_id)s | %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
            "json": {
                "()": "logging.Formatter",
                "format": (
                    '{"timestamp": "%(asctime)s", '
                    '"level": "%(levelname)s", '
                    '"logger": "%(name)s", '
                    '"request_id": "%(request_id)s", '
                    '"message": "%(message)s"}'
                ),
                "datefmt": "%Y-%m-%dT%H:%M:%S",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": formatter_name,
                "level": log_level,
                "stream": "ext://sys.stdout",
                "filters": ["request_id"],
            },
            "file_app": {
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": formatter_name,
                "level": log_level,
                "filename": os.path.join(log_dir, "app.log"),
                "maxBytes": 5 * 1024 * 1024,
                "backupCount": 3,
                "encoding": "utf-8",
                "filters": ["request_id"],
            },
            "file_api": {
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": formatter_name,
                "level": log_level,
                "filename": os.path.join(log_dir, "api.log"),
                "maxBytes": 5 * 1024 * 1024,
                "backupCount": 3,
                "encoding": "utf-8",
                "filters": ["request_id"],
            },
            "file_agents": {
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": formatter_name,
                "level": log_level,
                "filename": os.path.join(log_dir, "agents.log"),
                "maxBytes": 5 * 1024 * 1024,
                "backupCount": 3,
                "encoding": "utf-8",
                "filters": ["request_id"],
            },
            "file_services": {
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": formatter_name,
                "level": log_level,
                "filename": os.path.join(log_dir, "services.log"),
                "maxBytes": 5 * 1024 * 1024,
                "backupCount": 3,
                "encoding": "utf-8",
                "filters": ["request_id"],
            },
            "file_clients": {
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": formatter_name,
                "level": log_level,
                "filename": os.path.join(log_dir, "clients.log"),
                "maxBytes": 5 * 1024 * 1024,
                "backupCount": 3,
                "encoding": "utf-8",
                "filters": ["request_id"],
            },
            "file_utils": {
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": formatter_name,
                "level": log_level,
                "filename": os.path.join(log_dir, "utils.log"),
                "maxBytes": 5 * 1024 * 1024,
                "backupCount": 3,
                "encoding": "utf-8",
                "filters": ["request_id"],
            },
        },
        "loggers": {
            "app": {
                "handlers": ["console", "file_app"],
                "level": log_level,
                "propagate": False,
            },
            "api": {
                "handlers": ["console", "file_api"],
                "level": log_level,
                "propagate": False,
            },
            "agents": {
                "handlers": ["console", "file_agents"],
                "level": log_level,
                "propagate": False,
            },
            "services": {
                "handlers": ["console", "file_services"],
                "level": log_level,
                "propagate": False,
            },
            "clients": {
                "handlers": ["console", "file_clients"],
                "level": log_level,
                "propagate": False,
            },
            "utils": {
                "handlers": ["console", "file_utils"],
                "level": log_level,
                "propagate": False,
            },
            # fallback для всього іншого
            "": {
                "handlers": ["console", "file_app"],
                "level": log_level,
                "propagate": True,
            },
        },
    }


def configure_logging() -> None:
    config = get_logging_config()
    logging.config.dictConfig(config)
