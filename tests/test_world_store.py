from __future__ import annotations

import pytest

from app.schemas.world import (
    NPCSprites,
    SceneBible,
    SpriteSet,
    WorldAssets,
    WorldSpec,
)
from app.services.world_store import WorldStore


@pytest.fixture
def sample_bible():
    return SceneBible(
        world=WorldSpec(place="cafe", time_of_day="afternoon", weather="sunny",
                        mood="cozy", ambient_sounds=["rain"], bgm_mood="warm",
                        art_style_prompt="watercolor"),
        npcs=[],
        cross_relationships=[],
    )


def test_store_and_get(sample_bible):
    store = WorldStore()
    wid = store.put(sample_bible)
    assert wid.startswith("w_")
    retrieved = store.get(wid)
    assert retrieved is not None
    assert retrieved.world.place == "cafe"


def test_get_unknown_returns_none():
    store = WorldStore()
    assert store.get("w_nonexistent") is None


def test_get_or_raise(sample_bible):
    store = WorldStore()
    wid = store.put(sample_bible)
    assert store.get_or_raise(wid).world.place == "cafe"


def test_get_or_raise_unknown():
    store = WorldStore()
    import app.errors
    with pytest.raises(app.errors.WorldNotFoundError):
        store.get_or_raise("w_bad")


def test_put_assets_and_get():
    store = WorldStore()
    assets = WorldAssets(background_base64="aaaa", sprites=[
        NPCSprites(entity_id="e1", sprites=SpriteSet(default="bbbb")),
    ])
    store.put_assets("w_test", assets)
    retrieved = store.get_assets("w_test")
    assert retrieved is not None
    assert retrieved.background_base64 == "aaaa"
