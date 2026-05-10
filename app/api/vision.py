"""POST /api/vision/analyze endpoint."""
from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends, File, Request, UploadFile

from app.adapters.factory import build_vision_adapter
from app.config import Settings, get_settings
from app.errors import (
    InvalidInputError,
    PayloadTooLargeError,
    RateLimitedError,
    UnsafeImageError,
    UnsupportedMediaError,
)
from app.schemas.vision import VisionAnalyzeResponse
from app.services.vision_service import VisionService
from app.utils.ratelimit import MemoryRateLimiter

router = APIRouter(prefix="/api/vision", tags=["vision"])
log = structlog.get_logger("pll.vision")

# 单实例进程内的限流器。create_app() 启动时按 settings 重建。
_RATE_LIMITER: MemoryRateLimiter | None = None


def _ensure_limiter(settings: Settings) -> MemoryRateLimiter:
    global _RATE_LIMITER
    if _RATE_LIMITER is None:
        _RATE_LIMITER = MemoryRateLimiter(
            max_per_window=settings.rate_limit_vision_per_min,
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


@router.post("/analyze", response_model=VisionAnalyzeResponse)
async def analyze_image(
    request: Request,
    image: UploadFile = File(default=None),  # noqa: B008
    settings: Settings = Depends(get_settings),  # noqa: B008
) -> VisionAnalyzeResponse:
    if image is None or image.filename is None:
        raise InvalidInputError("missing required field 'image'")

    # MIME 校验
    mime = (image.content_type or "").lower()
    if mime not in settings.upload_allowed_mime:
        raise UnsupportedMediaError(mime or "<unknown>")

    # 限流
    limiter = _ensure_limiter(settings)
    ok, retry_after = limiter.check(_client_ip(request))
    if not ok:
        raise RateLimitedError(retry_after_s=retry_after)

    # 读取 + 大小校验
    image_bytes = await image.read()
    if len(image_bytes) > settings.upload_max_bytes:
        raise PayloadTooLargeError(
            f"file is {len(image_bytes)} bytes, max {settings.upload_max_bytes}"
        )

    # 调用业务
    adapter = build_vision_adapter(settings)
    service = VisionService(adapter=adapter)
    result = await service.analyze(image_bytes)

    if not result.is_safe:
        log.info("vision.unsafe", reasons=result.reject_reasons)
        raise UnsafeImageError(reasons=result.reject_reasons)

    request_id = request.headers.get("x-request-id", "req_unknown")
    log.info("vision.ok", objects=len(result.objects), request_id=request_id)

    return VisionAnalyzeResponse(
        request_id=request_id,
        is_safe=True,
        reject_reasons=[],
        scene_summary=result.scene_summary,
        objects=result.objects,
    )
