"""Tests for revised vision_safety prompt (v3 — Living Scene)."""
from __future__ import annotations


def test_system_prompt_does_not_mention_face_rejection():
    from app.prompts.vision_safety import build_vision_safety_messages

    msgs = build_vision_safety_messages(image_data_url="data:image/png;base64,x")
    sys_msg = next(m["content"] for m in msgs if m["role"] == "system")
    # The new prompt should NOT instruct the model to reject faces as unsafe.
    assert "real human faces" not in sys_msg
    assert "face_detected" not in sys_msg


def test_system_prompt_includes_entities_key():
    from app.prompts.vision_safety import build_vision_safety_messages

    msgs = build_vision_safety_messages(image_data_url="data:image/png;base64,x")
    sys_msg = next(m["content"] for m in msgs if m["role"] == "system")
    assert "entities" in sys_msg
    assert "character" in sys_msg
    assert "kind" in sys_msg
    assert "salience" in sys_msg


def test_system_prompt_includes_raw_scene():
    from app.prompts.vision_safety import build_vision_safety_messages

    msgs = build_vision_safety_messages(image_data_url="data:image/png;base64,x")
    sys_msg = next(m["content"] for m in msgs if m["role"] == "system")
    assert "raw_scene" in sys_msg


def test_system_prompt_retains_safety_checks():
    from app.prompts.vision_safety import build_vision_safety_messages

    msgs = build_vision_safety_messages(image_data_url="data:image/png;base64,x")
    sys_msg = next(m["content"] for m in msgs if m["role"] == "system")
    # Should still check NSFW / violence / weapons / sensitive symbols
    assert "nsfw" in sys_msg.lower() or "NSFW" in sys_msg
    assert "violence" in sys_msg
    assert "weapons" in sys_msg
    assert "sensitive" in sys_msg
