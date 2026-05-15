"""E2E test for Living Scene happy path using all fake adapters."""
from __future__ import annotations

import asyncio
import os

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture(autouse=True)
def _force_fake_providers(monkeypatch):
    """Override .env settings to use fake adapters for E2E tests."""
    monkeypatch.setenv("PLL_AI_VISION_PROVIDER", "fake")
    monkeypatch.setenv("PLL_AI_LLM_PROVIDER", "fake")
    monkeypatch.setenv("PLL_AI_TTS_PROVIDER", "fake")
    monkeypatch.setenv("PLL_AI_IMAGEGEN_PROVIDER", "fake")
    monkeypatch.setenv("PLL_AI_STT_PROVIDER", "fake")
    # Prevent .env values from leaking in
    for key in list(os.environ.keys()):
        if key.startswith("PLL_") and "PROVIDER" not in key and "RATE_LIMIT" not in key:
            monkeypatch.delenv(key, raising=False)


@pytest.mark.asyncio
async def test_living_scene_full_flow(monkeypatch):
    monkeypatch.setenv("PLL_RATE_LIMIT_VISION_PER_MIN", "100")

    from app.main import create_app

    app = create_app()
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Step 1: Upload an image
        image_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 128
        resp = await ac.post(
            "/api/vision/analyze",
            files={"image": ("test.png", image_bytes, "image/png")},
            data={"user_level": "beginner"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["is_safe"] is True
        assert data.get("world_id", "") != ""
        assert len(data.get("entities", [])) >= 1

        # Step 2: Poll world SSE until ready
        world_id = data["world_id"]

        # The async background gen should complete quickly with fakes
        await asyncio.sleep(0.5)

        world_resp = await ac.get(f"/api/world/{world_id}")
        assert world_resp.status_code == 200
        assert "text/event-stream" in world_resp.headers.get("content-type", "")
