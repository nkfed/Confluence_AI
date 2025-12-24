import time
import functools
import inspect
from typing import Callable, Any, Coroutine

from src.core.logging.logger import get_logger


def log_timing(func: Callable) -> Callable:
    """
    Декоратор для логування часу виконання функцій (sync та async).
    Автоматично використовує логер модуля, де визначена функція.
    """

    logger = get_logger(func.__module__)

    if inspect.iscoroutinefunction(func):
        # async function
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            start = time.perf_counter()
            try:
                result = await func(*args, **kwargs)
                duration = (time.perf_counter() - start) * 1000
                logger.info(f"{func.__name__} took {duration:.2f} ms")
                return result
            except Exception:
                duration = (time.perf_counter() - start) * 1000
                logger.exception(f"{func.__name__} failed after {duration:.2f} ms")
                raise

        return wrapper

    else:
        # sync function
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            start = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                duration = (time.perf_counter() - start) * 1000
                logger.info(f"{func.__name__} took {duration:.2f} ms")
                return result
            except Exception:
                duration = (time.perf_counter() - start) * 1000
                logger.exception(f"{func.__name__} failed after {duration:.2f} ms")
                raise

        return wrapper
