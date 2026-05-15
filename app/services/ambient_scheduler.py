"""AmbientScheduler: per-session coroutine emitting ambient NPC events."""
from __future__ import annotations

import asyncio
import random

import structlog

from app.adapters.llm.base import LLMAdapter
from app.prompts.ambient_mumble import build_mumble_message
from app.schemas.ambient import AmbientEvent
from app.schemas.world import NPCSpec, SceneBible

log = structlog.get_logger("pll.service.ambient_scheduler")

WEIGHTS = {"glance": 0.70, "gesture": 0.20, "mumble": 0.10}
MUMBLE_CHAR_LIMIT = 6


class AmbientScheduler:
    def __init__(
        self,
        llm: LLMAdapter,
        bible: SceneBible,
    ) -> None:
        self._llm = llm
        self._bible = bible
        self._min_interval = 15
        self._max_interval = 45

    async def run(
        self,
        active_npc_id: str,
        is_streaming: callable,
        ws_send: callable,
    ) -> None:
        """Main loop: emit ambient events while the session is alive."""
        while True:
            await asyncio.sleep(random.uniform(self._min_interval, self._max_interval))
            if is_streaming():
                continue

            npc = self._pick_npc(active_npc_id)
            if npc is None:
                continue

            event_type = self._weighted_choice(WEIGHTS)
            event = await self._build_event(event_type, npc, active_npc_id)
            if event:
                try:
                    await ws_send(event.model_dump())
                except Exception as exc:
                    log.warning("ambient.send_failed", error=str(exc))

    def _pick_npc(self, active_npc_id: str) -> NPCSpec | None:
        others = [
            n for n in self._bible.npcs
            if n.entity_id != active_npc_id
        ]
        if not others:
            return None
        # Prefer NPCs with cross_relationships to active NPC
        related_ids = {
            r.from_entity for r in self._bible.cross_relationships
        } | {r.to_entity for r in self._bible.cross_relationships}
        related = [n for n in others if n.entity_id in related_ids]
        if related:
            return random.choice(related)
        return random.choice(others)

    async def _build_event(
        self, event_type: str, npc: NPCSpec, active_npc_id: str
    ) -> AmbientEvent | None:
        if event_type == "glance":
            return AmbientEvent(
                npc_id=npc.entity_id, event="glance",
                target=active_npc_id, duration_ms=1000,
            )
        elif event_type == "gesture":
            return AmbientEvent(
                npc_id=npc.entity_id, event="gesture", duration_ms=800,
            )
        elif event_type == "mumble":
            try:
                msgs = build_mumble_message(
                    persona_name=npc.persona_name,
                    personality=npc.personality,
                    role_in_scene=npc.role_in_scene,
                    place=self._bible.world.place,
                )
                text = await self._llm.generate(msgs, temperature=0.8)
                text = text.strip().strip("\"'")
                if len(text) > MUMBLE_CHAR_LIMIT * 2:
                    text = text[:MUMBLE_CHAR_LIMIT * 2] + "..."
                return AmbientEvent(
                    npc_id=npc.entity_id, event="mumble",
                    text=text, duration_ms=3000,
                )
            except Exception as exc:
                log.warning("ambient.mumble_failed", error=str(exc))
                return None
        return None

    @staticmethod
    def _weighted_choice(weights: dict[str, float]) -> str:
        r = random.random()
        cumulative = 0.0
        for key, weight in weights.items():
            cumulative += weight
            if r <= cumulative:
                return key
        return "glance"
