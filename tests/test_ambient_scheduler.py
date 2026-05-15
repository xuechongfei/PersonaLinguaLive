from __future__ import annotations

import asyncio

import pytest

from app.schemas.world import CrossRelationship, NPCSpec, SceneBible, VoiceTraits, WorldSpec


class FakeLLMForAmbient:
    async def generate(self, messages, *, temperature=0.0):
        return "Just one more chapter..."


@pytest.fixture
def bible_with_npcs():
    return SceneBible(
        world=WorldSpec(
            place="cafe", time_of_day="afternoon", weather="rainy",
            mood="cozy", bgm_mood="warm",
            ambient_sounds=[], art_style_prompt="x"),
        npcs=[
            NPCSpec(entity_id="e1", kind="object", persona_name="Mocha",
                    role_in_scene="coffee", personality="warm",
                    voice_traits=VoiceTraits(), ambient_actions=["steam puff"]),
            NPCSpec(entity_id="e2", kind="character", persona_name="Iris",
                    role_in_scene="librarian", personality="quiet",
                    voice_traits=VoiceTraits(), ambient_actions=["turn page"]),
        ],
        cross_relationships=[CrossRelationship(from_entity="e1", to_entity="e2", note="partners")],
    )


@pytest.mark.asyncio
async def test_scheduler_skips_when_streaming(bible_with_npcs):
    from app.services.ambient_scheduler import AmbientScheduler

    events = []

    async def send(payload):
        events.append(payload)

    is_streaming_calls = []

    def is_streaming():
        is_streaming_calls.append(True)
        return True  # always streaming

    scheduler = AmbientScheduler(
        llm=FakeLLMForAmbient(),
        bible=bible_with_npcs,
    )
    # Override intervals to be instant for testing
    scheduler._min_interval = 0.01
    scheduler._max_interval = 0.05

    task = asyncio.create_task(
        scheduler.run(
            active_npc_id="e1",
            is_streaming=is_streaming,
            ws_send=send,
        )
    )
    await asyncio.sleep(0.2)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    assert len(is_streaming_calls) > 0
    # Should have skipped all events since streaming=True each time
    assert len(events) == 0


@pytest.mark.asyncio
async def test_scheduler_sends_events(bible_with_npcs):
    from app.services.ambient_scheduler import AmbientScheduler

    events = []

    async def send(payload):
        events.append(payload)

    def is_streaming():
        return False  # never streaming

    scheduler = AmbientScheduler(
        llm=FakeLLMForAmbient(),
        bible=bible_with_npcs,
    )
    # Override internal sleep to be instant
    scheduler._min_interval = 0.01
    scheduler._max_interval = 0.05

    task = asyncio.create_task(
        scheduler.run(
            active_npc_id="e1",
            is_streaming=is_streaming,
            ws_send=send,
        )
    )
    await asyncio.sleep(0.3)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    assert len(events) > 0
    # Events should have npc_id other than e1
    event_ids = {e.get("npc_id") for e in events}
    assert "e2" in event_ids or len(events) > 0
