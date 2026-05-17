"""SceneBibleService generates the SceneBible via LLM with retry and optional judge."""
from __future__ import annotations

import json

import structlog

from app.adapters.llm.base import LLMAdapter
from app.errors import SceneBibleParseError
from app.prompts.scene_bible import build_scene_bible_messages
from app.schemas.vision import Entity
from app.schemas.world import SceneBible
from app.services.world_store import WorldStore

log = structlog.get_logger("pll.service.scene_bible")

MAX_RETRIES = 2


class SceneBibleService:
    def __init__(self, *, llm: LLMAdapter, world_store: WorldStore | None = None) -> None:
        self._llm = llm
        self._store = world_store

    async def generate(
        self,
        *,
        raw_scene: str,
        entities: list[Entity] | list[dict],
        user_level: str = "beginner",
        max_npcs: int = 6,
    ) -> SceneBible:
        entity_dicts = _to_dicts(entities)
        messages = build_scene_bible_messages(
            raw_scene=raw_scene,
            entities=entity_dicts,
            user_level=user_level,
            max_npcs=max_npcs,
        )
        last_err: Exception | None = None
        for attempt in range(MAX_RETRIES):
            try:
                raw = await self._llm.generate(messages, temperature=0.3)
                clean = _extract_json(raw)
                bible = SceneBible.model_validate_json(clean)
                _align_entity_ids(bible, entity_dicts, max_npcs)
                return bible
            except (json.JSONDecodeError, ValueError) as exc:
                log.warning("scene_bible.parse_retry", attempt=attempt + 1, error=str(exc))
                last_err = exc
        raise SceneBibleParseError(str(last_err or "unknown parse error"))

    async def generate_stored(
        self,
        *,
        raw_scene: str,
        entities: list[Entity] | list[dict],
        user_level: str = "beginner",
        max_npcs: int = 6,
    ) -> str:
        """Generate a SceneBible, store it, and return the world_id."""
        if self._store is None:
            raise RuntimeError("WorldStore is required for generate_stored")
        bible = await self.generate(
            raw_scene=raw_scene,
            entities=entities,
            user_level=user_level,
            max_npcs=max_npcs,
        )
        return self._store.put(bible)


def _to_dicts(entities: list[Entity] | list[dict]) -> list[dict]:
    out: list[dict] = []
    for e in entities:
        if isinstance(e, dict):
            out.append(e)
        else:
            out.append({
                "id": e.id,
                "kind": e.kind,
                "label": e.label,
                "salience": e.salience,
                "persona_seed": e.seed,
            })
    return out


def _extract_json(raw: str) -> str:
    """Extract JSON from LLM output, handling markdown fences."""
    stripped = raw.strip()
    if stripped.startswith("```"):
        start = stripped.find("\n")
        end = stripped.rfind("```")
        if start != -1 and end > start:
            stripped = stripped[start + 1:end].strip()
    return stripped


def _align_entity_ids(bible: SceneBible, entity_dicts: list[dict], max_npcs: int) -> None:
    """Force-rewrite each npc.entity_id back to the vision-provided id by position.

    The prompt asks the LLM to copy entity_id verbatim, but in practice models
    reassign them (e.g. e0/e1/e2 -> e1/e2/e3). Since the prompt also constrains
    output to the top N entities by salience in input order, position alignment
    is reliable for the common case and degrades gracefully when the LLM drops
    or adds entries.
    """
    original_ids = [str(d.get("id", "")) for d in entity_dicts[:max_npcs] if d.get("id")]
    id_set = set(original_ids)
    needs_align = any(npc.entity_id not in id_set for npc in bible.npcs)
    if not needs_align:
        return

    id_map: dict[str, str] = {}
    for i, npc in enumerate(bible.npcs):
        if i >= len(original_ids):
            break
        old_id = npc.entity_id
        new_id = original_ids[i]
        if old_id != new_id:
            id_map[old_id] = new_id
            npc.entity_id = new_id

    for rel in bible.cross_relationships:
        if rel.from_entity in id_map:
            rel.from_entity = id_map[rel.from_entity]
        if rel.to_entity in id_map:
            rel.to_entity = id_map[rel.to_entity]

    if id_map:
        log.info("scene_bible.entity_id_aligned", remapped=id_map)
