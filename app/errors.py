"""Domain errors and FastAPI exception handlers."""
from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class PLLError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        http_status: int = 500,
        details: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status
        self.details = details or {}
        self.headers = headers or {}


class InvalidInputError(PLLError):
    def __init__(self, message: str) -> None:
        super().__init__("INVALID_INPUT", message, http_status=400)


class PayloadTooLargeError(PLLError):
    def __init__(self, message: str) -> None:
        super().__init__("PAYLOAD_TOO_LARGE", message, http_status=413)


class UnsupportedMediaError(PLLError):
    def __init__(self, mime: str) -> None:
        super().__init__(
            "UNSUPPORTED_MEDIA",
            f"unsupported media type: {mime}",
            http_status=415,
            details={"mime": mime},
        )


class UnsafeImageError(PLLError):
    def __init__(self, *, reasons: list[str]) -> None:
        super().__init__(
            "UNSAFE_IMAGE",
            "image rejected by content safety check",
            http_status=422,
            details={"reject_reasons": list(reasons)},
        )


class RateLimitedError(PLLError):
    def __init__(self, *, retry_after_s: int) -> None:
        super().__init__(
            "RATE_LIMITED",
            "rate limit exceeded",
            http_status=429,
            details={"retry_after_s": retry_after_s},
            headers={"Retry-After": str(retry_after_s)},
        )


class UpstreamFailureError(PLLError):
    def __init__(self, *, provider: str, message: str = "upstream provider failed") -> None:
        super().__init__(
            "UPSTREAM_FAILURE",
            message,
            http_status=502,
            details={"provider": provider},
        )
        self.provider = provider


class UpstreamTimeoutError(PLLError):
    def __init__(self, *, provider: str) -> None:
        super().__init__(
            "UPSTREAM_TIMEOUT",
            "upstream provider timed out",
            http_status=504,
            details={"provider": provider},
        )
        self.provider = provider


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(PLLError)
    async def _pll_error_handler(_request: Request, exc: PLLError) -> JSONResponse:
        body = {"code": exc.code, "message": exc.message, "details": exc.details}
        return JSONResponse(body, status_code=exc.http_status, headers=exc.headers)
