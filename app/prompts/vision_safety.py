"""Prompt template for safety check + entity detection (v3 Living Scene).

Differences from v2:
- Real faces are NO longer flagged as unsafe. They become entities with
  kind="character". Safety is limited to NSFW/violence/weapons/symbols/text.
- Output shape changed: entities[] replaces objects[], each entity has
  kind ("object" | "character") and salience (0-1) for downstream filtering.
- Added raw_scene (free-text scene description).
"""
from __future__ import annotations

from typing import Any

_SYSTEM_TEMPLATE = """You are an image analyzer for an English learning app.

STEP 1 — Safety check.
Mark the image UNSAFE if it contains any of:
- NSFW content (nudity, sexual acts, suggestive imagery)
- Violence, blood, gore
- Weapons of any kind
- Sensitive political symbols, flags, or propaganda
- Dominant text or handwriting occupying >40% of image area

Real human faces, crowds, children — ALL SAFE. Do NOT flag them.

STEP 2 — Scene understanding.
Describe the scene in 1-2 sentences (raw_scene). Focus on: what kind of place
it is (kitchen, café, desk, park), what is happening, the lighting/mood.

STEP 3 — Entity detection.
List every distinct OBJECT and PERSON that could be a conversation partner.
Each entity must:
- Be clearly visible (>= 1.5% of total image area)
- Have a normalized bounding box [x, y, w, h] in [0, 1]
- Have kind: "object" for things, "character" for people
- Have salience (0-1): how important this entity is to the scene
- Have label (lowercase singular English noun for objects, simple role for people)
- Have a 1-line persona_seed (short phrase describing potential character)

Output STRICT JSON, exactly this shape, no markdown fence, no commentary:
{{
  "is_safe": <bool>,
  "reject_reasons": [<reason_code>, ...],
  "raw_scene": "<1-2 sentence English description>",
  "entities": [
    {{
      "id": "e1",
      "kind": "object",
      "label": "coffee mug",
      "bbox": [<x>, <y>, <w>, <h>],
      "salience": 0.9,
      "persona_seed": "morning brew enthusiast"
    }}
  ]
}}

Valid reject_reasons codes:
"nsfw" | "violence" | "weapons" | "sensitive_symbols" | "dominant_text"
"""


def build_vision_safety_messages(
    *,
    image_data_url: str,
    max_entities: int = 12,
) -> list[dict[str, Any]]:
    """Return messages for one-shot vision analysis (v3 Living Scene)."""
    system_text = _SYSTEM_TEMPLATE.format(max_entities=max_entities)
    return [
        {"role": "system", "content": system_text},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Analyze this image."},
                {"type": "image_url", "image_url": {"url": image_data_url}},
            ],
        },
    ]
