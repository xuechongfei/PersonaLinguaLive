"""Tests for voice_picker — maps persona traits to MiniMax voice IDs."""
from __future__ import annotations

import pytest


def test_female_warm_returns_female_voice():
    from app.services.voice_picker import pick_voice

    voice_id = pick_voice({"gender": "female", "age": "adult", "tone": "warm"})
    assert "female" in voice_id.lower() or "woman" in voice_id.lower()


def test_male_gruff_returns_male_voice():
    from app.services.voice_picker import pick_voice

    voice_id = pick_voice({"gender": "male", "age": "adult", "tone": "gruff"})
    assert "male" in voice_id.lower() or "man" in voice_id.lower()


def test_child_returns_child_voice():
    from app.services.voice_picker import pick_voice

    voice_id = pick_voice({"gender": "female", "age": "child", "tone": "playful"})
    assert "child" in voice_id.lower() or "kid" in voice_id.lower() or "young" in voice_id.lower()


def test_empty_traits_returns_fallback():
    from app.services.voice_picker import pick_voice

    voice_id = pick_voice({})
    assert voice_id == "English_expressive_narrator"


def test_unknown_gender_returns_fallback():
    from app.services.voice_picker import pick_voice

    voice_id = pick_voice({"gender": "robot", "age": "adult", "tone": "warm"})
    assert voice_id == "English_expressive_narrator"


def test_pick_voice_is_deterministic():
    from app.services.voice_picker import pick_voice

    traits = {"gender": "female", "age": "adult", "tone": "warm"}
    assert pick_voice(traits) == pick_voice(traits)


@pytest.mark.parametrize(
    "gender,expected_keyword",
    [("female", "female"), ("male", "male")],
)
def test_each_gender_maps_to_distinct_voice_pool(gender, expected_keyword):
    from app.services.voice_picker import pick_voice

    voice_id = pick_voice({"gender": gender, "age": "adult", "tone": "neutral"})
    assert expected_keyword in voice_id.lower()
