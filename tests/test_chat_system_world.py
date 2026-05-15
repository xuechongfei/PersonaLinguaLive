from __future__ import annotations

import pytest

from app.prompts.chat_system import build_chat_system_message_world
from app.schemas.world import CrossRelationship, NPCSpec, SceneBible, VoiceTraits, WorldSpec


@pytest.fixture
def sample_bible():
    return SceneBible(
        world=WorldSpec(
            place="cafe", time_of_day="afternoon", weather="rainy",
            mood="cozy", ambient_sounds=["rain_on_window"], bgm_mood="warm",
            art_style_prompt="watercolor",
        ),
        npcs=[
            NPCSpec(
                entity_id="e1", kind="object", persona_name="Mocha",
                role_in_scene="afternoon coffee", relationship_to_user="loyal companion",
                personality="warm, philosophical", voice_traits=VoiceTraits(),
                vocab_focus=["cozy", "steam"],
            ),
            NPCSpec(
                entity_id="e3", kind="character", persona_name="Iris",
                role_in_scene="librarian",
                relationship_to_user="familiar regular",
                personality="quiet but observant",
                voice_traits=VoiceTraits(gender="female", tone="warm"),
                vocab_focus=["chapter", "verse"],
            ),
        ],
        cross_relationships=[
            CrossRelationship(from_entity="e1", to_entity="e3", note="Iris ordered Mocha today"),
        ],
    )


def test_build_chat_system_message_includes_world(sample_bible):
    msg = build_chat_system_message_world(
        persona_name="Mocha", active_npc=sample_bible.npcs[0],
        bible=sample_bible, user_level="beginner",
    )
    content = msg["content"]
    # World details
    assert "cafe" in content
    assert "afternoon" in content
    assert "rainy" in content
    # Grounding rules
    assert "GROUNDING" in content or "sensory" in content
    # Other souls
    assert "Iris" in content
    assert "You are Mocha" in content


def test_build_does_not_speak_for_others(sample_bible):
    msg = build_chat_system_message_world(
        persona_name="Mocha", active_npc=sample_bible.npcs[0],
        bible=sample_bible, user_level="beginner",
    )
    content = msg["content"]
    assert "CANNOT speak for" in content


def test_level_instructions_included(sample_bible):
    msg = build_chat_system_message_world(
        persona_name="Mocha", active_npc=sample_bible.npcs[0],
        bible=sample_bible, user_level="intermediate",
    )
    content = msg["content"]
    assert "intermediate" in content.lower()
