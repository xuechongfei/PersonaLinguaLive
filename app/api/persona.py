"""POST /api/persona/generate endpoint."""
from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends, Request

from app.adapters.factory import build_llm_adapter
from app.config import Settings, get_settings
from app.errors import RateLimitedError
from app.schemas.persona import PersonaGenerateRequest, PersonaGenerateResponse
from app.services.persona_service import PersonaService
from app.utils.ratelimit import MemoryRateLimiter

router = APIRouter(prefix="/api/persona", tags=["persona"])
log = structlog.get_logger("pll.persona")

# 单实例进程内的限流器。create_app() 启动时按 settings 重建。
_RATE_LIMITER: MemoryRateLimiter | None = None


def _ensure_limiter(settings: Settings) -> MemoryRateLimiter:
    global _RATE_LIMITER
    if _RATE_LIMITER is None:
        _RATE_LIMITER = MemoryRateLimiter(
            max_per_window=settings.rate_limit_persona_per_min,
            window_seconds=60.0,
        )
    return _RATE_LIMITER


def reset_rate_limiter() -> None:
    """For tests: drop the singleton between create_app() calls."""
    global _RATE_LIMITER
    _RATE_LIMITER = None


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@router.post("/generate", response_model=PersonaGenerateResponse)
async def generate_persona(
    request: Request,
    body: PersonaGenerateRequest,
    settings: Settings = Depends(get_settings),  # noqa: B008
) -> PersonaGenerateResponse:
    # 限流
    limiter = _ensure_limiter(settings)
    ok, retry_after = limiter.check(_client_ip(request))
    if not ok:
        raise RateLimitedError(retry_after_s=retry_after)

    # 调用业务
    adapter = build_llm_adapter(settings)
    service = PersonaService(llm=adapter)
    result = await service.generate_persona(body)

    request_id = request.headers.get("x-request-id", "req_unknown")
    log.info("persona.ok", persona_name=result.persona_name, request_id=request_id)

    return result
