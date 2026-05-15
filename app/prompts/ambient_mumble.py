"""Lightweight prompt for ambient mumble generation."""
from __future__ import annotations


def build_mumble_message(
    persona_name: str,
    personality: str,
    role_in_scene: str,
    place: str,
    recent_chat_context: str = "",
) -> list[dict]:
    system = (
        f"You are {persona_name}, {role_in_scene} at {place}. "
        f"Personality: {personality}. "
        "Generate ONE very short piece of ambient dialogue (max 6 words) "
        "that this character would say to themselves in this moment. "
        "Output JUST the dialogue text, no quotes, no formatting, no explanation. "
        "Make it natural and subtle — like a quiet thought."
    )
    if recent_chat_context:
        system += f"\n\nRecent conversation nearby: {recent_chat_context}"

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": "What do you say?"},
    ]
