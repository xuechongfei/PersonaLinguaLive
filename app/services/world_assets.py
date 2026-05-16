"""WorldAssetsService: orchestrates parallel background+NPC sprite generation."""
from __future__ import annotations

import asyncio
import base64

import structlog

from app.adapters.imagegen.base import ImageGenAdapter
from app.prompts.background_gen import build_background_prompt
from app.prompts.sprite_gen import build_sprite_prompt
from app.schemas.world import NPCSpec, NPCSprites, SceneBible, SpriteSet, WorldAssets

log = structlog.get_logger("pll.service.world_assets")


class WorldAssetsService:
    def __init__(self, imagegen: ImageGenAdapter) -> None:
        self._imagegen = imagegen

    async def generate_world(
        self,
        bible: SceneBible,
        source_image_bytes: bytes,
    ) -> WorldAssets:
        # Sequential to avoid rate limits on free-tier imagegen APIs
        bg_base64 = await self._generate_background(bible, source_image_bytes)

        sprite_results = []
        for npc in bible.npcs:
            sprite_results.append(await self._generate_npc_sprites(bible, npc))
            await asyncio.sleep(0.5)  # small gap between NPCs

        return WorldAssets(
            background_base64=bg_base64,
            sprites=sprite_results,
        )

    async def _generate_background(self, bible: SceneBible, source_image: bytes) -> str:
        prompt = build_background_prompt(
            place=bible.world.place,
            time_of_day=bible.world.time_of_day,
            weather=bible.world.weather,
            art_style=bible.world.art_style_prompt,
        )
        result = await self._imagegen.image_to_image(source_image, prompt)
        return base64.b64encode(result.image_bytes).decode("utf-8")

    async def _generate_npc_sprites(self, bible: SceneBible, npc: NPCSpec) -> NPCSprites:
        default_result = await self._imagegen.text_to_image(
            build_sprite_prompt(
                persona_name=npc.persona_name,
                role_in_scene=npc.role_in_scene,
                art_style=bible.world.art_style_prompt,
                kind=npc.kind,
                frame_type="default",
            ),
        )
        default_b64 = base64.b64encode(default_result.image_bytes).decode()

        blink_b64 = await self._gen_frame(npc, bible, "blink", default_result.image_bytes)

        return NPCSprites(
            entity_id=npc.entity_id,
            sprites=SpriteSet(
                default=default_b64,
                blink=blink_b64,
            ),
        )

    async def _gen_frame(self, npc: NPCSpec, bible: SceneBible, frame_type: str, reference: bytes) -> str:
        prompt = build_sprite_prompt(
            persona_name=npc.persona_name,
            role_in_scene=npc.role_in_scene,
            art_style=bible.world.art_style_prompt,
            kind=npc.kind,
            frame_type=frame_type,
        )
        result = await self._imagegen.text_to_image(
            prompt, reference_image=reference,
        )
        return base64.b64encode(result.image_bytes).decode()
