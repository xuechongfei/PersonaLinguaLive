"""Integration tests for POST /api/vision/analyze using FakeVisionAdapter."""
from __future__ import annotations

from io import BytesIO

import pytest
from fastapi.testclient import TestClient

from tests.fixtures.images import (
    fake_face_bytes,
    fake_nsfw_bytes,
    safe_png_bytes,
)


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("PLL_AI_VISION_PROVIDER", "fake")
    monkeypatch.setenv("PLL_RATE_LIMIT_VISION_PER_MIN", "100")  # 防止测试相互限流
    from app.main import create_app

    return TestClient(create_app())


def _multipart(image_bytes: bytes, mime: str = "image/png", filename: str = "test.png"):
    return {"image": (filename, BytesIO(image_bytes), mime)}


def test_safe_image_returns_objects(client):
    resp = client.post("/api/vision/analyze", files=_multipart(safe_png_bytes()))
    assert resp.status_code == 200
    body = resp.json()
    assert body["is_safe"] is True
    assert body["reject_reasons"] == []
    assert body["scene_summary"]
    assert len(body["objects"]) >= 1
    obj0 = body["objects"][0]
    assert {"id", "label", "bbox", "persona_seed"} <= set(obj0.keys())
    assert {"x", "y", "w", "h"} == set(obj0["bbox"].keys())


def test_safe_image_response_includes_request_id(client):
    resp = client.post(
        "/api/vision/analyze",
        files=_multipart(safe_png_bytes()),
        headers={"X-Request-ID": "req_test_xyz"},
    )
    assert resp.status_code == 200
    assert resp.json()["request_id"] == "req_test_xyz"
    assert resp.headers.get("x-request-id") == "req_test_xyz"


def test_face_image_returns_200_safe_in_v3(client):
    resp = client.post("/api/vision/analyze", files=_multipart(fake_face_bytes()))
    assert resp.status_code == 200
    body = resp.json()
    assert body["is_safe"] is True


def test_nsfw_image_returns_422_unsafe(client):
    resp = client.post("/api/vision/analyze", files=_multipart(fake_nsfw_bytes()))
    assert resp.status_code == 422
    assert "nsfw" in resp.json()["details"]["reject_reasons"]


def test_missing_image_field_returns_400(client):
    resp = client.post("/api/vision/analyze", data={})
    # FastAPI's own validation -> 422 from Pydantic on missing form field;
    # but our endpoint normalizes that to INVALID_INPUT 400 via dependency.
    assert resp.status_code in (400, 422)


def test_unsupported_mime_returns_415(client):
    resp = client.post(
        "/api/vision/analyze",
        files={"image": ("face.gif", BytesIO(b"GIF89a"), "image/gif")},
    )
    assert resp.status_code == 415
    assert resp.json()["code"] == "UNSUPPORTED_MEDIA"


def test_oversized_payload_returns_413(client, monkeypatch):
    monkeypatch.setenv("PLL_UPLOAD_MAX_BYTES", "1024")  # 1KB
    from app.main import create_app

    small_client = TestClient(create_app())
    resp = small_client.post(
        "/api/vision/analyze",
        files=_multipart(b"\x89PNG" + b"\x00" * 2048),  # >1KB
    )
    assert resp.status_code == 413
    assert resp.json()["code"] == "PAYLOAD_TOO_LARGE"


def test_rate_limited_returns_429(monkeypatch):
    monkeypatch.setenv("PLL_AI_VISION_PROVIDER", "fake")
    monkeypatch.setenv("PLL_RATE_LIMIT_VISION_PER_MIN", "2")
    from app.main import create_app

    c = TestClient(create_app())
    for _ in range(2):
        r = c.post("/api/vision/analyze", files=_multipart(safe_png_bytes()))
        assert r.status_code == 200
    r = c.post("/api/vision/analyze", files=_multipart(safe_png_bytes()))
    assert r.status_code == 429
    assert r.json()["code"] == "RATE_LIMITED"
    assert "retry-after" in {k.lower() for k in r.headers.keys()}
