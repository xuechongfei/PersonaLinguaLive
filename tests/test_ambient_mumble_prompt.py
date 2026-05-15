from __future__ import annotations

from app.prompts.ambient_mumble import build_mumble_message


def test_build_mumble_message_includes_npc_and_world():
    msg = build_mumble_message(
        persona_name="Mocha",
        personality="warm and philosophical",
        role_in_scene="afternoon coffee",
        place="cafe",
    )
    combined = str(msg)
    assert "Mocha" in combined
    assert "cafe" in combined
    assert "warm" in combined


def test_build_mumble_message_has_short_character_limit():
    msg = build_mumble_message(
        persona_name="Iris", personality="quiet",
        role_in_scene="librarian", place="library",
    )
    content = next(m["content"] for m in msg if m["role"] == "system")
    assert "short" in content.lower() or "6" in content
