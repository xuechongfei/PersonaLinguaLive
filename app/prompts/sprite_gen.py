"""Prompt builder for NPC sprite generation (text-to-image)."""
from __future__ import annotations


def build_sprite_prompt(
    persona_name: str,
    role_in_scene: str,
    art_style: str,
    kind: str = "object",
    frame_type: str = "default",
) -> str:
    base = (
        f"A {art_style} illustration of a character named {persona_name}, "
        f"who is {role_in_scene}. "
        f"Transparent background, game-style character portrait."
    )
    if kind == "object":
        base += " This character IS the object itself, anthropomorphized slightly."
    if frame_type == "default":
        base += " Neutral expression, eyes open, standing/idle pose."
    elif frame_type == "blink":
        base += " Same character, same pose, eyes closed (blinking)."
    elif frame_type in ("mouth_a", "mouth_b", "mouth_c"):
        openness = {"mouth_a": "mouth slightly open (small vowel sound)",
                    "mouth_b": "mouth moderately open (normal speech)",
                    "mouth_c": "mouth wide open (loud vowel sound)"}
        base += f" Same character, same pose, {openness[frame_type]}."
    return base
