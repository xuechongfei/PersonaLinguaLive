"""Tests for the learner-context prompt builder."""
from __future__ import annotations

from app.prompts.learner_context import build_learner_context_message


def test_returns_none_when_no_signal() -> None:
    assert build_learner_context_message(None, None, None) is None
    assert build_learner_context_message("", [], []) is None
    assert build_learner_context_message("   ", [" "], [""]) is None


def test_level_only_message() -> None:
    msg = build_learner_context_message("intermediate", [], [])
    assert msg is not None
    assert msg["role"] == "system"
    assert "intermediate" in msg["content"]


def test_includes_recent_vocab_and_caps_at_20() -> None:
    words = [f"word{i}" for i in range(30)]
    msg = build_learner_context_message("beginner", words, [])
    assert msg is not None
    content = msg["content"]
    assert "word0" in content
    assert "word19" in content
    assert "word20" not in content


def test_includes_weak_areas() -> None:
    msg = build_learner_context_message(
        "advanced",
        ["foo"],
        ["past tense usage", "phrasal verbs"],
    )
    assert msg is not None
    assert "past tense usage" in msg["content"]
    assert "phrasal verbs" in msg["content"]


def test_skips_empty_strings_in_lists() -> None:
    msg = build_learner_context_message("beginner", ["", " ", "real"], [""])
    assert msg is not None
    assert "real" in msg["content"]
    # Should not have the empty-list area phrasing
    assert "Areas they're working on" not in msg["content"]
