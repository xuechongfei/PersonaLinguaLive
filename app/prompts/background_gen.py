"""Prompt builder for background image generation (image-to-image)."""
from __future__ import annotations


def build_background_prompt(
    place: str,
    time_of_day: str,
    weather: str,
    art_style: str,
) -> str:
    return (
        f"Transform this image into a {art_style} illustration. "
        f"The scene is a {place}, it's {time_of_day}, {weather}. "
        "Remove all real people from the scene — keep only the environment and objects. "
        "The scene should feel warm and inviting. "
        "No text, no speech bubbles, no words in the image."
    )
