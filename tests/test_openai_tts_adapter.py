"""Tests for OpenAITTSAdapter (httpx mocked via respx)."""
from __future__ import annotations

import httpx
import pytest
import respx

from app.errors import UpstreamFailureError, UpstreamTimeoutError


@pytest.mark.asyncio
@respx.mock
async def test_synthesize_returns_audio_bytes():
    from app.adapters.tts.openai_tts import OpenAITTSAdapter

    respx.post("https://api.openai.com/v1/audio/speech").mock(
        return_value=httpx.Response(200, content=b"fake-mp3-bytes")
    )

    adapter = OpenAITTSAdapter(api_key="sk-test", base_url="https://api.openai.com/v1", model="tts-1", timeout_s=10.0)
    result = await adapter.synthesize("Hello")
    assert result == b"fake-mp3-bytes"


@pytest.mark.asyncio
@respx.mock
async def test_http_500_raises_upstream_failure():
    from app.adapters.tts.openai_tts import OpenAITTSAdapter

    respx.post("https://api.openai.com/v1/audio/speech").mock(
        return_value=httpx.Response(500, text="server error")
    )

    adapter = OpenAITTSAdapter(api_key="sk-test", base_url="https://api.openai.com/v1", model="tts-1", timeout_s=10.0)
    with pytest.raises(UpstreamFailureError):
        await adapter.synthesize("Hello")


@pytest.mark.asyncio
@respx.mock
async def test_timeout_raises_upstream_timeout():
    from app.adapters.tts.openai_tts import OpenAITTSAdapter

    respx.post("https://api.openai.com/v1/audio/speech").mock(
        side_effect=httpx.TimeoutException("timed out")
    )

    adapter = OpenAITTSAdapter(api_key="sk-test", base_url="https://api.openai.com/v1", model="tts-1", timeout_s=10.0)
    with pytest.raises(UpstreamTimeoutError):
        await adapter.synthesize("Hello")


@pytest.mark.asyncio
@respx.mock
async def test_request_includes_authorization_header():
    from app.adapters.tts.openai_tts import OpenAITTSAdapter

    captured: dict = {}

    def _capture(request: httpx.Request) -> httpx.Response:
        captured["headers"] = dict(request.headers)
        import json
        captured["body"] = json.loads(request.content.decode())
        return httpx.Response(200, content=b"audio")

    respx.post("https://api.openai.com/v1/audio/speech").mock(side_effect=_capture)

    adapter = OpenAITTSAdapter(api_key="sk-secret", base_url="https://api.openai.com/v1", model="tts-1-hd", timeout_s=10.0)
    await adapter.synthesize("Hello", voice="nova")

    assert captured["headers"].get("authorization") == "Bearer sk-secret"
    assert captured["body"]["model"] == "tts-1-hd"
    assert captured["body"]["voice"] == "nova"
    assert captured["body"]["input"] == "Hello"
