import time
import asyncio
import functools
from typing import Callable, Any, Type, Tuple

from src.core.logging.logger import get_logger


def log_retry(
    attempts: int = 3,
    backoff: float = 1.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
):
    """
    Декоратор для retry-логіки з логуванням.
    Підтримує sync та async функції.
    """

    def decorator(func: Callable):
        logger = get_logger(func.__module__)

        # async version
        if asyncio.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs) -> Any:
                for attempt in range(1, attempts + 1):
                    try:
                        return await func(*args, **kwargs)
                    except exceptions as e:
                        if attempt == attempts:
                            logger.exception(
                                f"{func.__name__} failed after {attempts} attempts: {e}"
                            )
                            raise

                        delay = backoff * attempt
                        logger.warning(
                            f"{func.__name__} retry {attempt}/{attempts} after {delay:.1f}s due to: {e}"
                        )
                        await asyncio.sleep(delay)

            return async_wrapper

        # sync version
        else:

            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs) -> Any:
                for attempt in range(1, attempts + 1):
                    try:
                        return func(*args, **kwargs)
                    except exceptions as e:
                        if attempt == attempts:
                            logger.exception(
                                f"{func.__name__} failed after {attempts} attempts: {e}"
                            )
                            raise

                        delay = backoff * attempt
                        logger.warning(
                            f"{func.__name__} retry {attempt}/{attempts} after {delay:.1f}s due to: {e}"
                        )
                        time.sleep(delay)

            return sync_wrapper

    return decorator
