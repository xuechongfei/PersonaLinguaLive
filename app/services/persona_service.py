"""PersonaService: generates LLM-based personas with LRU cache."""
from __future__ import annotations

import json
from collections import OrderedDict
from uuid import uuid4

from app.adapters.llm.base import LLMAdapter
from app.prompts.persona_gen import build_persona_messages
from app.schemas.persona import PersonaGenerateRequest, PersonaGenerateResponse
from app.services.voice_picker import pick_voice


class PersonaService:
    """Orchestrates persona generation with an LLM and an LRU response cache."""

    def __init__(self, llm: LLMAdapter) -> None:
        self._llm = llm
        self._cache: OrderedDict[tuple, PersonaGenerateResponse] = OrderedDict()
        self._max_cache_size = 100

    async def generate_persona(
        self, request: PersonaGenerateRequest
    ) -> PersonaGenerateResponse:
        """Generate a persona, caching results keyed by request parameters."""
        key = (
            request.label,
            request.scene_summary,
            request.user_level,
            request.persona_seed,
        )

        # Cache hit -- return stored object directly (LRU bump)
        if key in self._cache:
            self._cache.move_to_end(key)
            return self._cache[key]

        # Cache miss -- call the LLM
        messages = build_persona_messages(
            label=request.label,
            scene_summary=request.scene_summary,
            user_level=request.user_level,
            persona_seed=request.persona_seed,
        )

        raw = await self._llm.generate(messages, temperature=0.8)

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Failed to parse LLM response as JSON: {exc}"
            ) from exc

        # Map LLM response fields to our schema.
        # The FakeLLMAdapter returns "personality_description" while the
        # prompt instructs real LLMs to output "description" -- accept both.
        try:
            response = PersonaGenerateResponse(
                persona_id=uuid4().hex[:8],
                persona_name=data["persona_name"],
                description=data.get(
                    "personality_description",
                    data.get("description", ""),
                ),
                system_prompt=data["system_prompt"],
                vocab_focus=data.get("vocab_focus", []),
                voice_id=pick_voice(data.get("voice_traits")),
            )
        except KeyError as exc:
            raise ValueError(
                f"Missing expected key in LLM response: {exc}"
            ) from exc

        # Store in LRU cache, evicting oldest entry if at capacity
        self._cache[key] = response
        self._cache.move_to_end(key)
        if len(self._cache) > self._max_cache_size:
            self._cache.popitem(last=False)

        return response

    def clear_cache(self) -> None:
        """Remove all cached personas."""
        self._cache.clear()
