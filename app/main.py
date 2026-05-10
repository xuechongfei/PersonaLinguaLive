"""FastAPI application factory."""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api import health
from app.api.deps import RequestIdMiddleware
from app.config import Settings


def create_app() -> FastAPI:
    settings = Settings()
    app = FastAPI(title=settings.app_name, version=settings.app_version)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestIdMiddleware)

    from app.errors import register_exception_handlers

    register_exception_handlers(app)

    app.include_router(health.router)

    from app.api import persona as persona_module
    from app.api import vision as vision_module

    vision_module.reset_rate_limiter()  # 新 app 实例 = 新限流器
    app.include_router(vision_module.router)

    persona_module.reset_rate_limiter()  # 新 app 实例 = 新限流器
    app.include_router(persona_module.router)

    _mount_spa_if_present(app, settings.frontend_dist_dir)
    return app


def _mount_spa_if_present(app: FastAPI, dist_dir: str) -> None:
    """生产模式:把 frontend/dist 挂到 / 与 /assets,并提供 SPA fallback。"""
    dist_path = Path(dist_dir)
    if not (dist_path / "index.html").exists():
        return

    assets_path = dist_path / "assets"
    if assets_path.exists():
        app.mount("/assets", StaticFiles(directory=assets_path), name="assets")

    index_file = dist_path / "index.html"

    @app.get("/", include_in_schema=False)
    async def _root():
        return FileResponse(index_file)

    @app.get("/{full_path:path}", include_in_schema=False)
    async def _spa_fallback(full_path: str):
        # 已知 API 路由前缀不应进入 fallback
        if full_path.startswith(("api/", "healthz", "assets/")):
            return FileResponse(index_file, status_code=404)
        target = dist_path / full_path
        if target.is_file():
            return FileResponse(target)
        return FileResponse(index_file)


app = create_app()
