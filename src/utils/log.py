"""
Утилітний модуль для логування.
Надає зручні функції info(), error(), debug(), audit(), log_json(), log_metrics() для запису в logs/utils.log.
"""
import logging
import json
from typing import Any, Optional, Union
from datetime import datetime

# Отримуємо логер "utils" (налаштований у logging_config.py)
_logger: logging.Logger | None = None


def _get_logger() -> logging.Logger:
    """
    Отримує логер "utils" з ледачою ініціалізацією.
    Гарантує, що логер налаштовується тільки один раз.
    """
    global _logger
    if _logger is None:
        from src.core.logging.logger import get_logger
        _logger = get_logger("utils")
    return _logger


def info(message: str, *args: Any, **kwargs: Any) -> None:
    """
    Записує INFO-повідомлення в logs/utils.log.
    
    Args:
        message: Повідомлення для логування
        *args: Додаткові аргументи для форматування
        **kwargs: Додаткові параметри для logger.info()
    
    Example:
        log.info("Processing page %s", page_id)
    """
    _get_logger().info(message, *args, **kwargs)


def error(message: str, *args: Any, **kwargs: Any) -> None:
    """
    Записує ERROR-повідомлення в logs/utils.log.
    
    Args:
        message: Повідомлення для логування
        *args: Додаткові аргументи для форматування
        **kwargs: Додаткові параметри для logger.error()
    
    Example:
        log.error("Failed to process page %s: %s", page_id, error)
    """
    _get_logger().error(message, *args, **kwargs)


def debug(message: str, *args: Any, **kwargs: Any) -> None:
    """
    Записує DEBUG-повідомлення в logs/utils.log.
    
    Args:
        message: Повідомлення для логування
        *args: Додаткові аргументи для форматування
        **kwargs: Додаткові параметри для logger.debug()
    
    Example:
        log.debug("Extracted %d characters from page", len(text))
    """
    _get_logger().debug(message, *args, **kwargs)


def warning(message: str, *args: Any, **kwargs: Any) -> None:
    """
    Записує WARNING-повідомлення в logs/utils.log.
    
    Args:
        message: Повідомлення для логування
        *args: Додаткові аргументи для форматування
        **kwargs: Додаткові параметри для logger.warning()
    
    Example:
        log.warning("Page %s not found in whitelist", page_id)
    """
    _get_logger().warning(message, *args, **kwargs)


def critical(message: str, *args: Any, **kwargs: Any) -> None:
    """
    Записує CRITICAL-повідомлення в logs/utils.log.
    
    Args:
        message: Повідомлення для логування
        *args: Додаткові аргументи для форматування
        **kwargs: Додаткові параметри для logger.critical()
    
    Example:
        log.critical("System failure: %s", error)
    """
    _get_logger().critical(message, *args, **kwargs)


def audit(message: str, actor: Optional[str] = None, action: Optional[str] = None) -> None:
    """
    Записує AUDIT-повідомлення про дії користувача або агента в logs/utils.log.
    
    Args:
        message: Основне повідомлення аудиту
        actor: Ім'я користувача/агента, що виконав дію (опціонально)
        action: Тип дії (опціонально)
    
    Example:
        log.audit("Tagged 5 pages", actor="BulkTaggingService", action="tag_pages")
        log.audit("User logged in", actor="john@example.com", action="login")
    """
    actor_str = f"[{actor}]" if actor else "[system]"
    action_str = f"[{action}]" if action else ""
    audit_message = f"[AUDIT] {actor_str} {action_str} {message}".strip()
    _get_logger().info(audit_message)


def log_json(data: dict, level: str = "INFO") -> None:
    """
    Серіалізує словник у JSON та записує в logs/utils.log.
    
    Args:
        data: Словник з даними для логування
        level: Рівень логування (INFO, ERROR, WARNING, DEBUG)
    
    Example:
        log.log_json({"page_id": "123", "tags": ["tag1", "tag2"]})
        log.log_json({"error": "Failed", "code": 500}, level="ERROR")
    """
    try:
        json_str = json.dumps(data, ensure_ascii=False, indent=None)
        level_upper = level.upper()
        
        if level_upper == "ERROR":
            _get_logger().error(f"JSON: {json_str}")
        elif level_upper == "WARNING":
            _get_logger().warning(f"JSON: {json_str}")
        elif level_upper == "DEBUG":
            _get_logger().debug(f"JSON: {json_str}")
        else:
            _get_logger().info(f"JSON: {json_str}")
    except Exception as e:
        _get_logger().error(f"Failed to serialize JSON data: {e}")


def log_to_db(data: dict, table: str = "logs") -> str:
    """
    Генерує SQL-запит INSERT для збереження логів у базу даних (SQLite/PostgreSQL).
    Функція НЕ виконує запит, тільки повертає SQL рядок для майбутнього використання.
    
    Args:
        data: Словник з даними для збереження
        table: Назва таблиці (за замовчуванням "logs")
    
    Returns:
        str: SQL-запит INSERT
    
    Example:
        sql = log.log_to_db({
            "level": "INFO",
            "message": "Page processed"
        })
        # Повертає: INSERT INTO logs (timestamp, level, message) 
        #            VALUES ('2025-12-26 12:00:00', 'INFO', 'Page processed');
    """
    if not data:
        return "-- Empty data, no INSERT generated for table " + table
    
    # Додаємо timestamp, якщо його немає
    if "timestamp" not in data:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        data = {"timestamp": timestamp, **data}
    
    # Формуємо список колонок
    columns = ", ".join(data.keys())
    
    # Формуємо список значень з екранізацією одинарних лапок
    escaped_values = []
    for value in data.values():
        # Конвертуємо значення в рядок та екранізуємо одинарні лапки
        str_value = str(value)
        escaped_value = str_value.replace("'", "''")
        escaped_values.append("'" + escaped_value + "'")
    
    values = ", ".join(escaped_values)
    
    # Формуємо фінальний SQL запит без вкладених escape-послідовностей
    sql = "INSERT INTO " + table + " (" + columns + ") VALUES (" + values + ");"
    
    # Логуємо для відстеження (тільки якщо логер вже ініціалізований)
    if _logger is not None:
        _get_logger().debug("Generated SQL: " + sql)
    
    return sql


def log_metrics(name: str, value: Union[int, float], tags: Optional[dict] = None) -> None:
    """
    Записує метрику в logs/utils.log у структурованому форматі.
    
    Args:
        name: Назва метрики
        value: Значення метрики (число)
        tags: Додаткові теги для класифікації метрики (опціонально)
    
    Example:
        log.log_metrics("pages_tagged", 42)
        log.log_metrics("api_response_time", 0.523, tags={"endpoint": "/bulk/tag-pages", "status": "success"})
        log.log_metrics("error_count", 3, tags={"service": "BulkTaggingService"})
    """
    tags_str = ""
    if tags:
        tags_json = json.dumps(tags, ensure_ascii=False)
        tags_str = f" tags={tags_json}"
    
    metric_message = f"[METRIC] {name}={value}{tags_str}"
    _get_logger().info(metric_message)


def log_rotation() -> dict:
    """
    Повертає інформацію про налаштування ротації логів.
    
    RotatingFileHandler вже налаштований у logging_config.py:
    - Максимальний розмір файлу: 5MB
    - Кількість бекапів: 3
    - Кодування: UTF-8
    
    Returns:
        dict: Інформація про налаштування ротації
    
    Example:
        info = log.log_rotation()
        print(info)
        # {'max_bytes': 5242880, 'backup_count': 3, 'encoding': 'utf-8', 'configured': True}
    """
    return {
        "max_bytes": 5 * 1024 * 1024,  # 5MB
        "backup_count": 3,
        "encoding": "utf-8",
        "configured": True,
        "note": "RotatingFileHandler налаштований у src/core/logging/logging_config.py"
    }
