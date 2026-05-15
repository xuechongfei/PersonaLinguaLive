from __future__ import annotations

from app.prompts.sprite_gen import build_sprite_prompt


def test_build_sprite_prompt_includes_npc_role():
    prompt = build_sprite_prompt(
        persona_name="Mocha",
        role_in_scene="afternoon coffee",
        art_style="watercolor cartoon",
        kind="object",
        frame_type="default",
    )
    assert "Mocha" in prompt
    assert "afternoon coffee" in prompt
    assert "watercolor" in prompt
