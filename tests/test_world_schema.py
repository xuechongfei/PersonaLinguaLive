"""Tests for world schemas (SceneBible, WorldAssets, etc.)."""
from __future__ import annotations

from app.schemas.world import (
    CrossRelationship,
    NPCSpec,
    SceneBible,
    VoiceTraits,
    WorldAssetStatus,
    WorldSpec,
)


def test_voice_traits_default():
    v = VoiceTraits()
    assert v.gender == "female"
    assert v.age == "adult"
    assert v.tone == "warm"


def test_npc_spec_minimal():
    n = NPCSpec(
        entity_id="e1", kind="object", persona_name="Mocha",
        role_in_scene="afternoon coffee",
        personality="warm",
        voice_traits=VoiceTraits(),
    )
    assert n.vocab_focus == []


def test_cross_relationship():
    r = CrossRelationship(from_entity="e1", to_entity="e2", note="partners")
    assert r.from_entity == "e1"


def test_scene_bible_round_trip():
    bible = SceneBible(
        world=WorldSpec(
            place="cafe", time_of_day="afternoon", weather="sunny",
            mood="cozy", ambient_sounds=["rain"], bgm_mood="warm",
            art_style_prompt="watercolor",
        ),
        npcs=[
            NPCSpec(
                entity_id="e1", kind="object", persona_name="Mocha",
                role_in_scene="coffee", personality="warm",
                voice_traits=VoiceTraits(),
            )
        ],
        cross_relationships=[],
    )
    assert len(bible.npcs) == 1
    assert bible.npcs[0].persona_name == "Mocha"


def test_world_asset_status():
    s = WorldAssetStatus(world_id="w_abc")
    assert s.state == "pending"
