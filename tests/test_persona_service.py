"""Tests for app.services.persona_service.PersonaService."""
from __future__ import annotations

import json

import pytest

from app.schemas.persona import PersonaGenerateRequest


class _StubAdapter:
    """Stub LLMAdapter that returns a configurable JSON response."""

    def __init__(self, response: str) -> None:
        self._response = response
        self.calls: list[list[dict]] = []

    async def generate(
        self,
        messages: list[dict],
        *,
        temperature: float = 0.7,
    ) -> str:
        self.calls.append(messages)
        return self._response


_VALID_JSON: str = json.dumps(
    {
        "persona_name": "Test Persona",
        "personality_description": "A test personality description.",
        "system_prompt": "You are a test persona.",
        "vocab_focus": ["test", "words"],
    }
)


def _make_request(**overrides: str) -> PersonaGenerateRequest:
    defaults: dict[str, str] = {
        "label": "test_object",
        "scene_summary": "a test scene",
        "user_level": "beginner",
        "persona_seed": "",
    }
    defaults.update(overrides)
    return PersonaGenerateRequest(**defaults)


# ---------------------------------------------------------------------------
# Cache behaviour
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cache_hit_returns_same_object() -> None:
    """A second call with the same request returns the cached object (is)."""
    from app.services.persona_service import PersonaService

    adapter = _StubAdapter(_VALID_JSON)
    svc = PersonaService(adapter)
    request = _make_request()

    r1 = await svc.generate_persona(request)
    r2 = await svc.generate_persona(request)

    assert r1 is r2
    assert len(adapter.calls) == 1  # LLM only called on first invocation


@pytest.mark.asyncio
async def test_cache_miss_calls_llm() -> None:
    """Different requests produce different responses (no false sharing)."""
    from app.services.persona_service import PersonaService

    adapter = _StubAdapter(_VALID_JSON)
    svc = PersonaService(adapter)

    r1 = await svc.generate_persona(_make_request(label="apple"))
    r2 = await svc.generate_persona(_make_request(label="banana"))

    assert r1 is not r2
    assert len(adapter.calls) == 2


@pytest.mark.asyncio
async def test_cache_eviction_when_over_max_size() -> None:
    """Oldest entry is evicted when cache exceeds max size."""
    from app.services.persona_service import PersonaService

    adapter = _StubAdapter(_VALID_JSON)
    svc = PersonaService(adapter)
    svc._max_cache_size = 2

    r_a = await svc.generate_persona(_make_request(label="a"))
    await svc.generate_persona(_make_request(label="b"))
    await svc.generate_persona(_make_request(label="c"))

    # "a" was the oldest and should have been evicted
    r_a_again = await svc.generate_persona(_make_request(label="a"))

    assert r_a is not r_a_again
    # LLM called: a, b, c, a (re-generated because evicted)
    assert len(adapter.calls) == 4


@pytest.mark.asyncio
async def test_clear_cache() -> None:
    """clear_cache forces a fresh LLM call on next request."""
    from app.services.persona_service import PersonaService

    adapter = _StubAdapter(_VALID_JSON)
    svc = PersonaService(adapter)
    request = _make_request()

    r1 = await svc.generate_persona(request)
    svc.clear_cache()
    r2 = await svc.generate_persona(request)

    assert r1 is not r2
    assert len(adapter.calls) == 2


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_json_decode_error_wraps_value_error() -> None:
    """Invalid JSON from the LLM raises ValueError with descriptive message."""
    from app.services.persona_service import PersonaService

    adapter = _StubAdapter("not valid json")
    svc = PersonaService(adapter)

    with pytest.raises(ValueError, match="Failed to parse"):
        await svc.generate_persona(_make_request())


@pytest.mark.asyncio
async def test_missing_key_raises_value_error() -> None:
    """JSON missing required keys raises ValueError with descriptive message."""
    from app.services.persona_service import PersonaService

    adapter = _StubAdapter(json.dumps({"persona_name": "alone"}))
    svc = PersonaService(adapter)

    with pytest.raises(ValueError, match="Missing expected key"):
        await svc.generate_persona(_make_request())


# ---------------------------------------------------------------------------
# Field mapping
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_field_mapping_personality_description_to_description() -> None:
    """personality_description from LLM maps to description in response."""
    from app.services.persona_service import PersonaService

    adapter = _StubAdapter(_VALID_JSON)
    svc = PersonaService(adapter)

    response = await svc.generate_persona(_make_request())

    assert response.description == "A test personality description."
