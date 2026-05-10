"""Tests for app.prompts.vision_safety."""
from __future__ import annotations


def test_build_messages_returns_system_and_user_pair():
    from app.prompts.vision_safety import build_vision_safety_messages

    messages = build_vision_safety_messages(image_data_url="data:image/jpeg;base64,abcd")
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"


def test_system_message_lists_unsafe_categories():
    from app.prompts.vision_safety import build_vision_safety_messages

    sys_msg = build_vision_safety_messages(image_data_url="data:image/png;base64,xx")[0]
    text = sys_msg["content"] if isinstance(sys_msg["content"], str) else sys_msg["content"][0]["text"]
    for kw in ["face", "NSFW", "violence", "weapon", "text"]:
        assert kw.lower() in text.lower()


def test_user_message_embeds_image_url_part():
    from app.prompts.vision_safety import build_vision_safety_messages

    user_msg = build_vision_safety_messages(image_data_url="data:image/jpeg;base64,zz")[1]
    parts = user_msg["content"]
    assert isinstance(parts, list)
    image_parts = [p for p in parts if p.get("type") == "image_url"]
    assert len(image_parts) == 1
    assert image_parts[0]["image_url"]["url"].startswith("data:image/jpeg;base64,")


def test_max_objects_propagated_into_prompt():
    from app.prompts.vision_safety import build_vision_safety_messages

    sys_msg = build_vision_safety_messages(
        image_data_url="data:image/jpeg;base64,xx",
        max_objects=8,
    )[0]
    text = sys_msg["content"] if isinstance(sys_msg["content"], str) else sys_msg["content"][0]["text"]
    assert "8" in text


def test_response_schema_keys_documented_in_system_prompt():
    from app.prompts.vision_safety import build_vision_safety_messages

    sys_msg = build_vision_safety_messages(image_data_url="data:image/jpeg;base64,xx")[0]
    text = sys_msg["content"] if isinstance(sys_msg["content"], str) else sys_msg["content"][0]["text"]
    for key in ["is_safe", "reject_reasons", "scene_summary", "objects"]:
        assert key in text
