"""GET /healthz — liveness check used by Docker / k8s / curl."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.config import Settings, get_settings

router = APIRouter()


@router.get("/healthz")
def healthz(settings: Settings = Depends(get_settings)) -> dict[str, str]:  # noqa: B008
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
    }
