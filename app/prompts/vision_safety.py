"""Prompt template for combined safety check + object detection."""
from __future__ import annotations

from typing import Any

_SYSTEM_TEMPLATE = """You are an image analyzer for an English learning app.

STEP 1 — Safety check.
Mark the image UNSAFE if it contains any of:
- REAL human faces (living people, including children and group photos). Animal faces
  (pets, wildlife, pandas, cats, dogs, etc.), statues, paintings, cartoons, toys,
  and plush figures are SAFE.
- NSFW content (nudity, sexual acts, suggestive imagery)
- Violence, blood
- Weapons of any kind
- Sensitive political symbols, flags, or propaganda
- Dominant text or handwriting (image is primarily text, occupying >40% area)

STEP 2 — If safe, list up to {max_objects} distinct prominent OBJECTS that could
be playful conversation partners. Each object must:
- Be clearly visible and >= 1.5% of total image area
- Have an English label (lowercase, singular noun)
- Have a normalized bounding box [x, y, w, h] in [0, 1]
- Have a 1-line persona seed (short phrase describing potential character)

Output STRICT JSON, exactly this shape, no markdown fence, no commentary:
{{
  "is_safe": <bool>,
  "reject_reasons": [<reason_code>, ...],
  "scene_summary": "<1-2 sentence English description>",
  "objects": [
    {{
      "label": "<noun>",
      "bbox": [<x>, <y>, <w>, <h>],
      "persona_seed": "<short phrase>"
    }}
  ]
}}

Valid reject_reasons codes:
"face_detected" | "nsfw" | "violence" | "weapons" | "sensitive_symbols" | "dominant_text" | "unclear_image"
"""


def build_vision_safety_messages(
    *,
    image_data_url: str,
    max_objects: int = 12,
) -> list[dict[str, Any]]:
    """Return OpenAI chat-completions style messages for one-shot vision analysis."""
    system_text = _SYSTEM_TEMPLATE.format(max_objects=max_objects)
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
