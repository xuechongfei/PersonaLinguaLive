"""HTTP middleware: attach a request_id to every request, expose on response."""
from __future__ import annotations

import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


class RequestIdMiddleware(BaseHTTPMiddleware):
    """读 X-Request-ID(若客户端给了),否则生成 req_<uuid hex>。"""

    HEADER = "X-Request-ID"

    async def dispatch(self, request: Request, call_next):
        incoming = request.headers.get(self.HEADER)
        rid = incoming if incoming else f"req_{uuid.uuid4().hex}"

        token = structlog.contextvars.bind_contextvars(request_id=rid)
        try:
            response = await call_next(request)
        finally:
            structlog.contextvars.unbind_contextvars("request_id")
            del token

        response.headers[self.HEADER] = rid
        return response
