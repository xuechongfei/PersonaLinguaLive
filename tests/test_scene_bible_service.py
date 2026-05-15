from __future__ import annotations

import json

import pytest

from app.schemas.world import SceneBible


class FakeLLM:
    def __init__(self, responses: list[str] | None = None):
        self.responses = responses or []
        self._idx = 0

    async def generate(self, messages, *, temperature=0.0):
        resp = self.responses[self._idx]
        self._idx += 1
        return resp


@pytest.mark.asyncio
async def test_generate_with_single_response():
    from app.services.scene_bible import SceneBibleService

    bible_json = json.dumps({
        "world": {
            "place": "cafe", "time_of_day": "afternoon", "weather": "sunny",
            "mood": "cozy", "ambient_sounds": ["rain"], "bgm_mood": "warm",
            "art_style_prompt": "watercolor",
        },
        "npcs": [
            {
                "entity_id": "e1", "kind": "object", "persona_name": "Mocha",
                "role_in_scene": "coffee", "relationship_to_user": "friend",
                "personality": "warm", "voice_traits": {"gender": "female", "age": "adult", "tone": "warm"},
                "vocab_focus": ["cozy"], "ambient_actions": ["steam"],
            }
        ],
        "cross_relationships": [],
    })

    llm = FakeLLM([bible_json])
    store = None  # not needed for generation alone
    service = SceneBibleService(llm=llm, world_store=store)
    bible = await service.generate(
        raw_scene="A cafe table",
        entities=[],
        user_level="beginner",
    )
    assert isinstance(bible, SceneBible)
    assert bible.world.place == "cafe"
    assert len(bible.npcs) == 1


@pytest.mark.asyncio
async def test_generate_with_invalid_json_raises():
    from app.services.scene_bible import SceneBibleService

    llm = FakeLLM(["this is not json", "still not json"])
    service = SceneBibleService(llm=llm, world_store=None)
    import app.errors
    with pytest.raises(app.errors.SceneBibleParseError):
        await service.generate(raw_scene="x", entities=[])


@pytest.mark.asyncio
async def test_generate_with_retry_on_failure():
    from app.services.scene_bible import SceneBibleService

    good = json.dumps({
        "world": {"place": "park", "time_of_day": "morning", "weather": "sunny",
                  "mood": "peaceful", "ambient_sounds": [], "bgm_mood": "warm",
                  "art_style_prompt": "sketch"},
        "npcs": [],
        "cross_relationships": [],
    })
    llm = FakeLLM(["bad json", good])
    service = SceneBibleService(llm=llm, world_store=None)
    bible = await service.generate(raw_scene="x", entities=[])
    assert bible.world.place == "park"
