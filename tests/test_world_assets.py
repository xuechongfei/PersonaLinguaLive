from __future__ import annotations

import pytest

from app.adapters.imagegen.base import ImageGenResult
from app.schemas.world import CrossRelationship, NPCSpec, SceneBible, VoiceTraits, WorldSpec


class FakeImageGen:
    def __init__(self):
        self.text_calls = []
        self.image_calls = []

    async def text_to_image(self, prompt, *, size="1024x1024", reference_image=None):
        self.text_calls.append(prompt)
        return ImageGenResult(b"\x89PNG", "image/png")

    async def image_to_image(self, image_bytes, prompt, *, size="1024x1024", strength=0.7):
        self.image_calls.append((prompt, len(image_bytes)))
        return ImageGenResult(b"\x89PNG", "image/png")


@pytest.fixture
def sample_bible():
    return SceneBible(
        world=WorldSpec(
            place="cafe", time_of_day="afternoon", weather="rainy",
            mood="cozy", ambient_sounds=["rain"], bgm_mood="warm",
            art_style_prompt="watercolor cartoon",
        ),
        npcs=[
            NPCSpec(
                entity_id="e1", kind="object", persona_name="Mocha",
                role_in_scene="afternoon coffee", personality="warm",
                voice_traits=VoiceTraits(),
            ),
            NPCSpec(
                entity_id="e2", kind="character", persona_name="Iris",
                role_in_scene="librarian on break", personality="thoughtful",
                voice_traits=VoiceTraits(gender="female", tone="warm"),
            ),
        ],
        cross_relationships=[
            CrossRelationship(from_entity="e1", to_entity="e2", note="coffee partner"),
        ],
    )


@pytest.mark.asyncio
async def test_generate_world_background_and_sprites(sample_bible):
    from app.services.world_assets import WorldAssetsService

    img_gen = FakeImageGen()
    service = WorldAssetsService(imagegen=img_gen)
    assets = await service.generate_world(sample_bible, b"source_image_bytes")

    assert assets.background_base64 != ""
    assert len(assets.sprites) == 2
    assert assets.sprites[0].entity_id == "e1"
    assert assets.sprites[1].entity_id == "e2"
    # Each sprite should have 5 frames
    assert assets.sprites[0].sprites.default != ""
    assert assets.sprites[0].sprites.blink != ""
    assert assets.sprites[1].sprites.mouth_a != ""
    # Background should have used image_to_image
    assert len(img_gen.image_calls) >= 1
    # Sprites should have used text_to_image
    assert len(img_gen.text_calls) >= 2


@pytest.mark.asyncio
async def test_background_is_image_to_image(sample_bible):
    from app.services.world_assets import WorldAssetsService

    img_gen = FakeImageGen()
    service = WorldAssetsService(imagegen=img_gen)
    await service.generate_world(sample_bible, b"src")
    assert any("watercolor" in c[0] for c in img_gen.image_calls)
