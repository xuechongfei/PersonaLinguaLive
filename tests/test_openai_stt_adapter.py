"""Tests for OpenAISTTAdapter (httpx mocked via respx)."""
from __future__ import annotations

import httpx
import pytest
import respx

from app.errors import UpstreamFailureError, UpstreamTimeoutError


@pytest.mark.asyncio
@respx.mock
async def test_transcribe_returns_text():
    from app.adapters.stt.openai_stt import OpenAISTTAdapter

    respx.post("https://api.openai.com/v1/audio/transcriptions").mock(
        return_value=httpx.Response(200, json={"text": "Hello world!"})
    )

    adapter = OpenAISTTAdapter(api_key="sk-test", base_url="https://api.openai.com/v1", model="whisper-1", timeout_s=10.0)
    result = await adapter.transcribe(b"fake-audio")
    assert result == "Hello world!"


@pytest.mark.asyncio
@respx.mock
async def test_transcribe_with_language():
    from app.adapters.stt.openai_stt import OpenAISTTAdapter

    def _check(request: httpx.Request) -> httpx.Response:
        assert b"language" in request.content
        return httpx.Response(200, json={"text": "Bonjour"})

    respx.post("https://api.openai.com/v1/audio/transcriptions").mock(side_effect=_check)

    adapter = OpenAISTTAdapter(api_key="sk-test", base_url="https://api.openai.com/v1", model="whisper-1", timeout_s=10.0)
    result = await adapter.transcribe(b"fake-audio", language="fr")
    assert result == "Bonjour"


@pytest.mark.asyncio
@respx.mock
async def test_http_500_raises_upstream_failure():
    from app.adapters.stt.openai_stt import OpenAISTTAdapter

    respx.post("https://api.openai.com/v1/audio/transcriptions").mock(
        return_value=httpx.Response(500, text="server error")
    )

    adapter = OpenAISTTAdapter(api_key="sk-test", base_url="https://api.openai.com/v1", model="whisper-1", timeout_s=10.0)
    with pytest.raises(UpstreamFailureError):
        await adapter.transcribe(b"fake-audio")


@pytest.mark.asyncio
@respx.mock
async def test_timeout_raises_upstream_timeout():
    from app.adapters.stt.openai_stt import OpenAISTTAdapter

    respx.post("https://api.openai.com/v1/audio/transcriptions").mock(
        side_effect=httpx.TimeoutException("timed out")
    )

    adapter = OpenAISTTAdapter(api_key="sk-test", base_url="https://api.openai.com/v1", model="whisper-1", timeout_s=10.0)
    with pytest.raises(UpstreamTimeoutError):
        await adapter.transcribe(b"fake-audio")
