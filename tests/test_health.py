"""Tests for the health endpoint."""
from __future__ import annotations

from fastapi.testclient import TestClient


def test_healthz_returns_ok():
    from app.main import create_app

    client = TestClient(create_app())
    resp = client.get("/healthz")

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["app"] == "PersonaLinguaLive"
    assert "version" in body
