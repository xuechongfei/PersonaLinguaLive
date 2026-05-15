from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.schemas.world import (
    SceneBible,
    WorldAssets,
    WorldSpec,
)


@pytest.fixture
def app():
    from app.main import create_app
    return create_app()


@pytest.mark.asyncio
async def test_get_world_returns_404_for_nonexistent(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/world/w_nonexistent")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_world_sse_returns_events(app):
    store = app.state.world_store
    bible = SceneBible(
        world=WorldSpec(place="cafe", time_of_day="afternoon", weather="rainy",
                        mood="cozy", ambient_sounds=["rain"], bgm_mood="warm",
                        art_style_prompt="watercolor"),
        npcs=[],
        cross_relationships=[],
    )
    wid = store.put(bible)
    store.put_assets(wid, WorldAssets(background_base64="aaaa"))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, timeout=5.0, base_url="http://test") as ac:
        resp = await ac.get(f"/api/world/{wid}")
    assert resp.status_code == 200
    assert resp.headers.get("content-type", "").startswith("text/event-stream")
