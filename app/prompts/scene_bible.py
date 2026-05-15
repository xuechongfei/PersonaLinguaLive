"""Prompt template for Scene Bible generation (v3 Living Scene).

Given raw_scene + entities from vision, the LLM produces a structured
SceneBible that defines: the world environment, NPC specs with personalities,
and cross-entity relationships.
"""
from __future__ import annotations

from typing import Any


_SYSTEM = """You are a world builder for an English learning app.

Given a scene description and a list of entities (objects and people),
create a "Scene Bible" — a complete specification for a cartoon living scene.

CRITICAL RULES:
- The scene MUST retain the original entities (they become NPCs).
- Only use the top {max_npcs} entities by salience as NPCs. Drop low-salience items.
- The world's art_style_prompt must describe a cartoon/illustration style
  that will be used for ALL image generation (background and sprites) to
  maintain visual consistency.
- ambient_sounds must only come from this list (comma-separated IDs):
  {allowed_sounds}. Pick 1-3.
- bgm_mood must be one of: warm, cozy, contemplative, playful, mysterious, energetic.
- Each NPC gets voice_traits for TTS voice selection.
- Each NPC gets ambient_actions: 2-4 short verb phrases for background behavior.

Output STRICT JSON, exactly this shape, no markdown:
{{
  "world": {{
    "place": "<string — where is this?>",
    "time_of_day": "<string — morning / afternoon / evening / night>",
    "weather": "<string — sunny / rainy / cloudy / ...>",
    "mood": "<string — one word feeling>",
    "ambient_sounds": ["<sound_id_1>", "<sound_id_2>"],
    "bgm_mood": "<string>",
    "art_style_prompt": "<detailed cartoon art style description>"
  }},
  "npcs": [
    {{
      "entity_id": "<from input>",
      "kind": "object|character",
      "persona_name": "<creative English name>",
      "role_in_scene": "<what this entity does in this scene>",
      "relationship_to_user": "<who they are to the user>",
      "personality": "<2-3 sentence personality>",
      "voice_traits": {{"gender": "female|male", "age": "child|adult|elder", "tone": "warm|sweet|confident|neutral|playful|gruff"}},
      "vocab_focus": ["<5-8 English vocab words>"],
      "ambient_actions": ["<verb phrase>", ...]
    }}
  ],
  "cross_relationships": [
    {{"from_entity": "<entity_id>", "to_entity": "<entity_id>", "note": "<their relationship>"}}
  ]
}}
"""


def build_scene_bible_messages(
    raw_scene: str,
    entities: list[dict[str, Any]],
    user_level: str = "beginner",
    max_npcs: int = 6,
    allowed_sounds: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Build messages for SceneBible LLM generation."""
    if allowed_sounds is None:
        allowed_sounds = [
            "rain_on_window", "espresso_machine", "page_turns",
            "cafe_chatter", "forest_birds", "wind_chimes", "keyboard_typing",
            "traffic_hum", "ocean_waves", "fire_crackling",
            "clock_ticking", "footsteps", "distant_laughter", "birdsong",
            "kitchen_sizzle", "water_pouring", "fan_hum", "dog_bark",
            "shower_run", "refrigerator_hum",
        ]

    system = _SYSTEM.format(max_npcs=max_npcs, allowed_sounds=", ".join(allowed_sounds))

    entity_lines = "\n".join(
        f"  - {e.get('id', '?')}: kind={e.get('kind', 'object')}, "
        f"label={e.get('label', '?')}, salience={e.get('salience', 0)}, "
        f"seed={e.get('persona_seed', e.get('seed', ''))}"
        for e in entities
    )

    user = (
        f"User level: {user_level}\n\n"
        f"Scene description:\n{raw_scene}\n\n"
        f"Detected entities (use first {max_npcs} by salience):\n{entity_lines}"
    )

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
