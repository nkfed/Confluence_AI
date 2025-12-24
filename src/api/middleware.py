import json
import time
import uuid
from typing import Any, Dict, List, Union
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, ContentStream
from starlette.types import Message

from src.core.logging.context import request_id_var
from src.core.logging.logger import get_logger

logger = get_logger("api")

SENSITIVE_KEYS = {
    "token", "access_token", "refresh_token", "password", "secret",
    "api_key", "authorization", "auth", "bearer"
}


def mask_sensitive_data(data: Any, max_string_length: int = 300) -> Any:
    """
    Рекурсивно проходить по структурах даних (dict/list),
    маскує чутливі поля та обрізає довгі рядки.
    """
    if isinstance(data, dict):
        return {
            k: mask_sensitive_data(v, max_string_length) if k.lower() not in SENSITIVE_KEYS else "***"
            for k, v in data.items()
        }
    elif isinstance(data, list):
        return [mask_sensitive_data(item, max_string_length) for item in data]
    elif isinstance(data, str):
        if len(data) > max_string_length:
            return data[:max_string_length] + "...[truncated]"
        return data
    return data


def safe_preview_body(raw_body: bytes, max_length: int = 500) -> str:
    """
    Спроба розпарсити JSON та замаскувати дані.
    Якщо не JSON - повертає обрізаний текст.
    """
    if not raw_body:
        return ""

    try:
        body_str = raw_body.decode("utf-8", errors="replace")
        try:
            data = json.loads(body_str)
            masked_data = mask_sensitive_data(data)
            preview = json.dumps(masked_data, ensure_ascii=False)
        except json.JSONDecodeError:
            preview = body_str

        if len(preview) > max_length:
            return preview[:max_length] + "...[truncated]"
        return preview
    except Exception:
        return "[Unable to preview body]"


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = str(uuid.uuid4())
        token = request_id_var.set(request_id)
        
        start_time = time.time()
        method = request.method
        path = request.url.path

        # Читаємо тіло запиту
        raw_body = await request.body()
        request_preview = safe_preview_body(raw_body)
        
        # Перевизначаємо receive, щоб FastAPI міг прочитати body знову
        async def receive() -> Message:
            return {"type": "http.request", "body": raw_body}

        request._receive = receive
        
        logger.info(f"Incoming request {method} {path} | body={request_preview}")
        
        try:
            response = await call_next(request)
            
            # Читаємо тіло відповіді
            response_body = b""
            async for chunk in response.body_iterator:
                response_body += chunk
            
            response_preview = safe_preview_body(response_body)
            
            process_time = (time.time() - start_time) * 1000
            formatted_process_time = "{0:.2f}".format(process_time)
            
            logger.info(
                f"Completed request: {method} {path} "
                f"status_code={response.status_code} duration={formatted_process_time}ms | response_body={response_preview}"
            )
            
            # Створюємо нову відповідь, бо body_iterator вичерпано
            new_response = Response(
                content=response_body,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type
            )
            new_response.headers["X-Request-ID"] = request_id
            
            return new_response
            
        except Exception as e:
            process_time = (time.time() - start_time) * 1000
            formatted_process_time = "{0:.2f}".format(process_time)
            
            logger.exception(
                f"Request failed: {method} {path} "
                f"error={str(e)} duration={formatted_process_time}ms"
            )
            raise
        finally:
            request_id_var.reset(token)
