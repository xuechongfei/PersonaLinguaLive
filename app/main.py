"""FastAPI application factory."""
from __future__ import annotations

from fastapi import FastAPI

from app.api import health
from app.api.deps import RequestIdMiddleware
from app.config import Settings


def create_app() -> FastAPI:
    settings = Settings()
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
    )
    app.add_middleware(RequestIdMiddleware)
    app.include_router(health.router)
    return app


app = create_app()
