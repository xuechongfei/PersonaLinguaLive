"""Prompt template for persona generation."""
from __future__ import annotations


def build_persona_messages(
    label: str,
    scene_summary: str,
    user_level: str = "beginner",
    persona_seed: str = "",
) -> list[dict]:
    """Build OpenAI chat-format messages to generate a persona for an object."""
    system = (
        "You are a persona generator for an English learning app. "
        "Given an object label and scene description, create a fun, memorable persona.\n\n"
        "Output strict JSON with these keys:\n"
        "- persona_name: a creative English name for this object\n"
        "- description: 1-2 sentence personality description in English\n"
        "- system_prompt: instructions for how this persona speaks (voice, attitude, vocabulary style)\n"
        "- vocab_focus: 3-6 English vocabulary words this persona would naturally teach\n"
        "- voice_traits: {gender, age, tone} for TTS voice selection\n"
        "    gender: 'female' | 'male'\n"
        "    age: 'child' | 'adult' | 'elder'\n"
        "    tone: 'warm' | 'sweet' | 'confident' | 'neutral' | 'playful' | 'gruff'\n\n"
        "The persona should:\n"
        "- Always speak in English\n"
        "- Match user level vocabulary complexity\n"
        "- Be friendly and encouraging\n"
        "- Stay in character as the object\n"
        "- Keep responses short (2-3 sentences per turn)"
    )

    user = (
        f"Object: {label}\n"
        f"Scene: {scene_summary}\n"
        f"User level: {user_level}\n"
    )
    if persona_seed:
        user += f"Personality hint: {persona_seed}\n"

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
