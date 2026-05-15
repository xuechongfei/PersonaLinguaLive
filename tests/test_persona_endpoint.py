"""Tests for deprecated POST /api/persona/generate (v0.3 — always 410)."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("PLL_AI_LLM_PROVIDER", "fake")
    from app.main import create_app
    return TestClient(create_app())


def test_generate_persona_returns_410_gone(client):
    resp = client.post(
        "/api/persona/generate",
        json={
            "label": "cupcake",
            "scene_summary": "A pink cupcake on a plate",
            "user_level": "beginner",
        },
    )
    assert resp.status_code == 410
    body = resp.json()
    assert "deprecated" in body["detail"].lower()
    assert "POST /api/vision/analyze" in body["detail"]


def test_generate_persona_with_seed_also_returns_410(client):
    resp = client.post(
        "/api/persona/generate",
        json={
            "label": "cupcake",
            "persona_seed": "The cupcake has pink frosting",
            "scene_summary": "A pink cupcake on a plate",
            "user_level": "beginner",
        },
    )
    assert resp.status_code == 410


def test_generate_persona_rate_limited_not_applicable(client):
    """Deprecated endpoint doesn't apply rate limiting."""
    resp = client.post(
        "/api/persona/generate",
        json={"label": "x", "scene_summary": "x", "user_level": "beginner"},
    )
    assert resp.status_code == 410
