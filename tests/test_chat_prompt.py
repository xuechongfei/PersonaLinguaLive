"""Tests for chat system prompt."""
from __future__ import annotations

from app.prompts.chat_system import build_chat_history_messages, build_chat_system_message


def test_system_message_contains_persona_name():
    msg = build_chat_system_message("Tilly", "A cheerful teacup", "Speak warmly")
    assert "Tilly" in msg["content"]
    assert msg["role"] == "system"


def test_system_message_contains_level_instructions():
    msg = build_chat_system_message("Bob", "A grumpy mug", "Be sarcastic", user_level="beginner")
    assert "simple sentences" in msg["content"].lower()


def test_different_levels_produce_different_instructions():
    beginner = build_chat_system_message("X", "desc", "prompt", user_level="beginner")
    advanced = build_chat_system_message("X", "desc", "prompt", user_level="advanced")
    assert beginner["content"] != advanced["content"]


def test_system_mentions_xml_tags():
    msg = build_chat_system_message("X", "desc", "prompt")
    assert "<speak>" in msg["content"]
    assert "<learning>" in msg["content"]
    assert "<followup>" in msg["content"]


def test_build_history_messages_filters_system():
    context = [
        {"role": "system", "content": "be a bot"},
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "hello"},
    ]
    history = build_chat_history_messages(context)
    assert len(history) == 2
    assert all(m["role"] in ("user", "assistant") for m in history)
