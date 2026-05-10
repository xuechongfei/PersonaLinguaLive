"""Tests for FakeLLMAdapter."""
from __future__ import annotations

import json
import pytest

from app.adapters.llm.fake import FakeLLMAdapter


@pytest.mark.asyncio
async def test_generate_returns_deterministic_persona_json():
    adapter = FakeLLMAdapter()
    result = await adapter.generate([{"role": "system", "content": "Generate a persona for the object."}])
    payload = json.loads(result)
    assert "persona_name" in payload
    assert "system_prompt" in payload
    assert payload["persona_name"] == "Tilly the Teacup"


@pytest.mark.asyncio
async def test_generate_returns_deterministic_chat_response():
    adapter = FakeLLMAdapter()
    result = await adapter.generate([{"role": "system", "content": "You are a friendly chatbot."}])
    assert "<speak>" in result
    assert "<learning>" in result


@pytest.mark.asyncio
async def test_generate_stream_yields_tokens():
    adapter = FakeLLMAdapter()
    tokens = []
    async for token in adapter.generate_stream([{"role": "system", "content": "Generate a persona."}]):
        tokens.append(token)
    assert len(tokens) > 0
    full = "".join(tokens)
    payload = json.loads(full)
    assert payload["persona_name"] == "Tilly the Teacup"


@pytest.mark.asyncio
async def test_generate_stream_yields_same_content_as_generate():
    adapter = FakeLLMAdapter()
    messages = [{"role": "system", "content": "Say hello."}]
    single = await adapter.generate(messages)
    tokens = []
    async for token in adapter.generate_stream(messages):
        tokens.append(token)
    assert "".join(tokens) == single


@pytest.mark.asyncio
async def test_records_last_messages():
    adapter = FakeLLMAdapter()
    messages = [{"role": "user", "content": "Hi"}]
    await adapter.generate(messages)
    assert adapter.last_messages == messages
