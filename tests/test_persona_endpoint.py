"""Integration tests for POST /api/persona/generate using FakeLLMAdapter."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("PLL_AI_LLM_PROVIDER", "fake")
    monkeypatch.setenv("PLL_RATE_LIMIT_PERSONA_PER_MIN", "100")  # 防止测试相互限流
    from app.main import create_app

    return TestClient(create_app())


def test_generate_persona_returns_200(client):
    resp = client.post(
        "/api/persona/generate",
        json={
            "label": "cupcake",
            "scene_summary": "A pink cupcake on a plate",
            "user_level": "beginner",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["persona_name"]
    assert body["description"]
    assert body["system_prompt"]
    assert isinstance(body["vocab_focus"], list)
    assert len(body["vocab_focus"]) > 0


def test_generate_persona_with_seed(client):
    resp = client.post(
        "/api/persona/generate",
        json={
            "label": "cupcake",
            "persona_seed": "The cupcake has pink frosting with a cherry on top",
            "scene_summary": "A pink cupcake on a plate",
            "user_level": "beginner",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["persona_name"]
    assert body["description"]


def test_generate_persona_returns_422_on_invalid_input(client):
    resp = client.post(
        "/api/persona/generate",
        json={"label": "", "scene_summary": "", "user_level": "beginner"},
    )
    assert resp.status_code == 422


def test_generate_persona_rate_limited(monkeypatch):
    monkeypatch.setenv("PLL_AI_LLM_PROVIDER", "fake")
    monkeypatch.setenv("PLL_RATE_LIMIT_PERSONA_PER_MIN", "1")
    from app.main import create_app

    c = TestClient(create_app())
    # First request should succeed
    r = c.post(
        "/api/persona/generate",
        json={
            "label": "cupcake",
            "scene_summary": "A pink cupcake on a plate",
            "user_level": "beginner",
        },
    )
    assert r.status_code == 200

    # Second request should be rate-limited
    r = c.post(
        "/api/persona/generate",
        json={
            "label": "cupcake",
            "scene_summary": "A pink cupcake on a plate",
            "user_level": "beginner",
        },
    )
    assert r.status_code == 429
    assert r.json()["code"] == "RATE_LIMITED"
    assert "retry-after" in {k.lower() for k in r.headers.keys()}
