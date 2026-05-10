"""Tests for persona generation prompt."""
from __future__ import annotations

from app.prompts.persona_gen import build_persona_messages


def test_returns_two_messages():
    messages = build_persona_messages(label="cupcake", scene_summary="A bright kitchen")
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"


def test_contains_label_and_scene():
    messages = build_persona_messages(label="cupcake", scene_summary="A bright kitchen")
    user = messages[1]["content"]
    assert "cupcake" in user
    assert "A bright kitchen" in user


def test_injects_user_level():
    messages = build_persona_messages(label="cup", scene_summary="desk", user_level="advanced")
    user = messages[1]["content"]
    assert "advanced" in user


def test_includes_persona_seed_when_provided():
    messages = build_persona_messages(label="cup", scene_summary="desk", persona_seed="cheerful baker")
    user = messages[1]["content"]
    assert "cheerful baker" in user


def test_system_prompt_requests_json_output():
    messages = build_persona_messages(label="cup", scene_summary="desk")
    system = messages[0]["content"]
    assert "persona_name" in system
    assert "description" in system
    assert "system_prompt" in system
    assert "vocab_focus" in system
