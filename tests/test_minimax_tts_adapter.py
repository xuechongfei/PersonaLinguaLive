"""Tests for MiniMaxTTSAdapter (httpx mocked via respx)."""
from __future__ import annotations

import json

import httpx
import pytest
import respx

from app.errors import UpstreamFailureError, UpstreamTimeoutError

MM_URL = "https://api.minimaxi.chat/v1/t2a_v2"


def _build_adapter():
    from app.adapters.tts.minimax_tts import MiniMaxTTSAdapter

    return MiniMaxTTSAdapter(
        api_key="sk-mm",
        group_id="grp123",
        base_url="https://api.minimaxi.chat/v1",
        model="speech-02-hd",
        default_voice="English_expressive_narrator",
        timeout_s=10.0,
    )


def _success_envelope(audio_hex: str) -> dict:
    return {
        "data": {"audio": audio_hex, "status": 2},
        "trace_id": "trace-x",
        "base_resp": {"status_code": 0, "status_msg": "success"},
    }


@pytest.mark.asyncio
@respx.mock
async def test_synthesize_decodes_hex_audio():

    audio_bytes = b"\xff\xfb\x50\xc4fake-mp3"
    respx.post(MM_URL).mock(
        return_value=httpx.Response(200, json=_success_envelope(audio_bytes.hex()))
    )

    adapter = _build_adapter()
    result = await adapter.synthesize("Hello")
    assert result == audio_bytes


@pytest.mark.asyncio
@respx.mock
async def test_request_uses_group_id_query_and_bearer_auth():
    captured: dict = {}

    def _capture(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["headers"] = dict(request.headers)
        captured["body"] = json.loads(request.content.decode())
        return httpx.Response(200, json=_success_envelope(b"abc".hex()))

    respx.post(MM_URL).mock(side_effect=_capture)

    adapter = _build_adapter()
    await adapter.synthesize("Hello", voice="English_friendly_female")

    assert "GroupId=grp123" in captured["url"]
    assert captured["headers"].get("authorization") == "Bearer sk-mm"
    assert captured["body"]["model"] == "speech-02-hd"
    assert captured["body"]["text"] == "Hello"
    assert captured["body"]["voice_setting"]["voice_id"] == "English_friendly_female"
    assert captured["body"]["audio_setting"]["format"] == "mp3"


@pytest.mark.asyncio
@respx.mock
async def test_default_voice_used_when_voice_arg_is_alloy_or_blank():
    """The orchestrator currently passes voice="alloy" (legacy default).
    For MiniMax, fall back to the configured default_voice in that case."""
    captured: dict = {}

    def _capture(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content.decode())
        return httpx.Response(200, json=_success_envelope(b"abc".hex()))

    respx.post(MM_URL).mock(side_effect=_capture)

    adapter = _build_adapter()
    await adapter.synthesize("Hello", voice="alloy")

    assert captured["body"]["voice_setting"]["voice_id"] == "English_expressive_narrator"


@pytest.mark.asyncio
@respx.mock
async def test_http_500_raises_upstream_failure():
    respx.post(MM_URL).mock(return_value=httpx.Response(500, text="server error"))

    adapter = _build_adapter()
    with pytest.raises(UpstreamFailureError) as exc_info:
        await adapter.synthesize("Hello")
    assert exc_info.value.provider == "minimax"


@pytest.mark.asyncio
@respx.mock
async def test_timeout_raises_upstream_timeout():
    respx.post(MM_URL).mock(side_effect=httpx.TimeoutException("timed out"))

    adapter = _build_adapter()
    with pytest.raises(UpstreamTimeoutError) as exc_info:
        await adapter.synthesize("Hello")
    assert exc_info.value.provider == "minimax"


@pytest.mark.asyncio
@respx.mock
async def test_application_error_in_base_resp_raises_upstream_failure():
    """HTTP 200 but base_resp.status_code != 0 = application-level failure."""
    bad_envelope = {
        "data": {},
        "base_resp": {"status_code": 1004, "status_msg": "voice_id not found"},
    }
    respx.post(MM_URL).mock(return_value=httpx.Response(200, json=bad_envelope))

    adapter = _build_adapter()
    with pytest.raises(UpstreamFailureError) as exc_info:
        await adapter.synthesize("Hello")
    assert "1004" in str(exc_info.value) or "voice_id not found" in str(exc_info.value)


@pytest.mark.asyncio
@respx.mock
async def test_missing_audio_field_raises_upstream_failure():
    bad_envelope = {
        "data": {"status": 2},  # no 'audio' key
        "base_resp": {"status_code": 0, "status_msg": "success"},
    }
    respx.post(MM_URL).mock(return_value=httpx.Response(200, json=bad_envelope))

    adapter = _build_adapter()
    with pytest.raises(UpstreamFailureError):
        await adapter.synthesize("Hello")


@pytest.mark.asyncio
@respx.mock
async def test_invalid_hex_in_audio_raises_upstream_failure():
    bad_envelope = {
        "data": {"audio": "not-valid-hex-string-zzz", "status": 2},
        "base_resp": {"status_code": 0, "status_msg": "success"},
    }
    respx.post(MM_URL).mock(return_value=httpx.Response(200, json=bad_envelope))

    adapter = _build_adapter()
    with pytest.raises(UpstreamFailureError):
        await adapter.synthesize("Hello")
