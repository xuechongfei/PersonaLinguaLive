"""POST /api/vision/analyze endpoint."""
from __future__ import annotations

import asyncio

import structlog
from fastapi import APIRouter, Depends, File, Form, Request, UploadFile

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
from app.services.scene_bible import SceneBibleService
from app.services.vision_service import VisionService
from app.services.world_assets import WorldAssetsService
from app.services.world_store import WorldStore
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
    user_level: str = Form("beginner"),  # noqa: B008
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
    log.info("vision.ok", entities=len(result.entities), request_id=request_id)

    # Generate SceneBible and spawn world asset generation
    world_id = ""
    world_store: WorldStore = request.app.state.world_store
    scene_bible_service: SceneBibleService = request.app.state.scene_bible_service
    world_assets_service: WorldAssetsService = request.app.state.world_assets_service

    if result.entities:
        try:
            bible = await scene_bible_service.generate(
                raw_scene=result.raw_scene or result.scene_summary,
                entities=result.entities,
                user_level=user_level,
            )
            world_id = world_store.put(bible)
            # Spawn background world asset generation
            asyncio.create_task(
                _generate_and_store_assets(
                    world_assets_service, bible, image_bytes, world_store, world_id
                )
            )
        except Exception:
            log.warning("vision.scene_bible_failed", request_id=request_id)
            world_id = ""

    return VisionAnalyzeResponse(
        request_id=request_id,
        is_safe=True,
        reject_reasons=[],
        scene_summary=result.scene_summary,
        raw_scene=result.raw_scene,
        objects=result.objects,
        entities=result.entities,
        world_id=world_id,
    )


async def _generate_and_store_assets(
    assets_service: WorldAssetsService,
    bible,
    image_bytes: bytes,
    world_store: WorldStore,
    world_id: str,
):
    try:
        assets = await assets_service.generate_world(bible, image_bytes)
        world_store.put_assets(world_id, assets)
    except Exception as exc:
        log.error("vision.world_assets_failed", world_id=world_id, error=str(exc))
        world_store.set_state(world_id, "error")
