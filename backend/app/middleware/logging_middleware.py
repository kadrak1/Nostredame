"""HTTP request logging middleware.

Binds a short ``request_id`` and ``ip`` to the structlog context for the
lifetime of each request, then emits an ``http_request`` log line with
method, path, HTTP status, and duration.
"""

import time
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.utils import get_client_ip

logger = structlog.get_logger("http")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log every HTTP request and bind request context to structlog."""

    async def dispatch(self, request: Request, call_next) -> Response:
        # Fresh context per request (contextvars are coroutine-local)
        structlog.contextvars.clear_contextvars()

        request_id = uuid.uuid4().hex[:12]  # 48 bits — low collision probability
        ip = get_client_ip(request)

        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            ip=ip,
        )

        start = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        except Exception:
            logger.error("http_request_error", exc_info=True)
            raise
        finally:
            duration_ms = round((time.perf_counter() - start) * 1000)
            logger.info(
                "http_request",
                method=request.method,
                path=request.url.path,
                status=status_code,
                duration_ms=duration_ms,
            )
