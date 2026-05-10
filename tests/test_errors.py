"""Tests for app.errors and global exception handler."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient


def _build_app_with_routes() -> FastAPI:
    from app.errors import (
        InvalidInputError,
        PayloadTooLargeError,
        PLLError,
        RateLimitedError,
        UnsafeImageError,
        UnsupportedMediaError,
        UpstreamFailureError,
        UpstreamTimeoutError,
        register_exception_handlers,
    )

    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/raise/{kind}")
    def _raise(kind: str):
        if kind == "invalid":
            raise InvalidInputError("missing field 'image'")
        if kind == "too-large":
            raise PayloadTooLargeError("file is 12MB, max 10MB")
        if kind == "unsupported":
            raise UnsupportedMediaError("image/gif")
        if kind == "unsafe":
            raise UnsafeImageError(reasons=["face_detected"])
        if kind == "rate":
            raise RateLimitedError(retry_after_s=42)
        if kind == "upstream-fail":
            raise UpstreamFailureError(provider="openai")
        if kind == "upstream-timeout":
            raise UpstreamTimeoutError(provider="openai")
        if kind == "base":
            raise PLLError("INTERNAL_ERROR", "boom", http_status=500)
        return {"ok": True}

    return app


def test_invalid_input_returns_400():
    resp = TestClient(_build_app_with_routes()).get("/raise/invalid")
    assert resp.status_code == 400
    assert resp.json()["code"] == "INVALID_INPUT"


def test_payload_too_large_returns_413():
    resp = TestClient(_build_app_with_routes()).get("/raise/too-large")
    assert resp.status_code == 413
    assert resp.json()["code"] == "PAYLOAD_TOO_LARGE"


def test_unsupported_media_returns_415():
    resp = TestClient(_build_app_with_routes()).get("/raise/unsupported")
    assert resp.status_code == 415
    assert resp.json()["code"] == "UNSUPPORTED_MEDIA"


def test_unsafe_image_returns_422_with_reasons():
    resp = TestClient(_build_app_with_routes()).get("/raise/unsafe")
    assert resp.status_code == 422
    body = resp.json()
    assert body["code"] == "UNSAFE_IMAGE"
    assert body["details"]["reject_reasons"] == ["face_detected"]


def test_rate_limited_returns_429_with_retry_after_header():
    resp = TestClient(_build_app_with_routes()).get("/raise/rate")
    assert resp.status_code == 429
    assert resp.json()["code"] == "RATE_LIMITED"
    assert resp.headers.get("retry-after") == "42"


def test_upstream_failure_returns_502():
    resp = TestClient(_build_app_with_routes()).get("/raise/upstream-fail")
    assert resp.status_code == 502
    assert resp.json()["code"] == "UPSTREAM_FAILURE"
    assert resp.json()["details"]["provider"] == "openai"


def test_upstream_timeout_returns_504():
    resp = TestClient(_build_app_with_routes()).get("/raise/upstream-timeout")
    assert resp.status_code == 504
    assert resp.json()["code"] == "UPSTREAM_TIMEOUT"


def test_base_pll_error_returns_custom_status():
    resp = TestClient(_build_app_with_routes()).get("/raise/base")
    assert resp.status_code == 500
    assert resp.json()["code"] == "INTERNAL_ERROR"
