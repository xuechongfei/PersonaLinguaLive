"""CORS preflight + static SPA fallback."""
from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient


def test_cors_allows_dev_origin():
    from app.main import create_app

    client = TestClient(create_app())
    resp = client.options(
        "/healthz",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_cors_blocks_unknown_origin():
    from app.main import create_app

    client = TestClient(create_app())
    resp = client.options(
        "/healthz",
        headers={
            "Origin": "https://evil.example.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    # FastAPI/Starlette 在 origin 不被允许时不附带 ACAO 头
    assert "access-control-allow-origin" not in {k.lower() for k in resp.headers}


def test_spa_fallback_serves_index_html(tmp_path, monkeypatch):
    dist = tmp_path / "frontend_dist"
    dist.mkdir()
    (dist / "index.html").write_text("<!doctype html><title>PLL</title>", encoding="utf-8")
    (dist / "assets").mkdir()
    (dist / "assets" / "app.js").write_text("console.log('ok')", encoding="utf-8")

    monkeypatch.setenv("PLL_FRONTEND_DIST_DIR", str(dist))

    from app.main import create_app

    client = TestClient(create_app())

    # 静态资源直出
    asset = client.get("/assets/app.js")
    assert asset.status_code == 200
    assert "console.log" in asset.text

    # 根路径 SPA fallback
    root = client.get("/")
    assert root.status_code == 200
    assert "<title>PLL</title>" in root.text


def test_spa_disabled_when_dist_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("PLL_FRONTEND_DIST_DIR", str(tmp_path / "nonexistent"))

    from app.main import create_app

    client = TestClient(create_app())
    # 此时根路径应是 404,不是崩溃
    resp = client.get("/")
    assert resp.status_code == 404
