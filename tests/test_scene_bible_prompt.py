"""Tests for scene_bible prompt assembly."""
from __future__ import annotations

from app.prompts.scene_bible import build_scene_bible_messages


def test_build_scene_bible_messages_contains_scene_content():
    msgs = build_scene_bible_messages(
        raw_scene="A cozy desk with coffee",
        entities=[],
        user_level="beginner",
    )
    joined = str(msgs)
    assert "A cozy desk with coffee" in joined


def test_build_scene_bible_messages_includes_entities():
    entities = [
        {"id": "e1", "kind": "object", "label": "mug", "salience": 0.9, "persona_seed": "warm"},
        {"id": "e2", "kind": "character", "label": "person", "salience": 0.6},
    ]
    msgs = build_scene_bible_messages(
        raw_scene="A cafe table", entities=entities, user_level="intermediate",
    )
    joined = str(msgs)
    assert "mug" in joined
    assert "person" in joined
    assert "character" in joined


def test_build_scene_bible_messages_output_shape():
    msgs = build_scene_bible_messages(
        raw_scene="Park bench", entities=[], user_level="advanced",
    )
    content = next(
        (m["content"] for m in msgs if m["role"] == "system"), ""
    )
    assert "npcs" in content
    assert "world" in content
