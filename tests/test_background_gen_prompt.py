from __future__ import annotations
from app.prompts.background_gen import build_background_prompt


def test_build_background_prompt_includes_world_fields():
    prompt = build_background_prompt(
        place="cafe", time_of_day="afternoon", weather="rainy",
        art_style="watercolor cartoon, warm palette",
    )
    assert "cafe" in prompt
    assert "afternoon" in prompt
    assert "rainy" in prompt
    assert "watercolor" in prompt
    assert "real people" in prompt.lower()
