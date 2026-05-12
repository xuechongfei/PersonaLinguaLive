"""Tests for QwenVisionAdapter (DashScope compatible-mode, mocked via respx)."""
from __future__ import annotations

import json

import httpx
import pytest
import respx

from app.errors import UpstreamFailureError, UpstreamTimeoutError
from tests.fixtures.images import safe_png_bytes

QWEN_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"


def _build_response(json_payload: dict) -> dict:
    """Wrap a vision JSON object in the OpenAI chat-completions envelope."""
    return {
        "id": "chatcmpl-q",
        "object": "chat.completion",
        "created": 0,
        "model": "qwen-vl-max-latest",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": json.dumps(json_payload)},
                "finish_reason": "stop",
            }
        ],
    }


def _build_adapter():
    from app.adapters.vision.qwen_vision import QwenVisionAdapter

    return QwenVisionAdapter(
        api_key="sk-qwen",
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        model="qwen-vl-max-latest",
        timeout_s=10.0,
    )


@pytest.mark.asyncio
@respx.mock
async def test_parses_safe_response_into_vision_result():
    payload = {
        "is_safe": True,
        "reject_reasons": [],
        "scene_summary": "A modern kitchen.",
        "objects": [
            {
                "label": "cupcake",
                "bbox": [0.4, 0.5, 0.2, 0.2],
                "persona_seed": "sweet baker",
            },
        ],
    }
    respx.post(QWEN_URL).mock(return_value=httpx.Response(200, json=_build_response(payload)))

    adapter = _build_adapter()
    result = await adapter.analyze_image(safe_png_bytes())

    assert result.is_safe is True
    assert result.scene_summary == "A modern kitchen."
    assert len(result.objects) == 1
    assert result.objects[0].label == "cupcake"


@pytest.mark.asyncio
@respx.mock
async def test_parses_unsafe_response():
    payload = {
        "is_safe": False,
        "reject_reasons": ["face_detected"],
        "scene_summary": "",
        "objects": [],
    }
    respx.post(QWEN_URL).mock(return_value=httpx.Response(200, json=_build_response(payload)))

    adapter = _build_adapter()
    result = await adapter.analyze_image(safe_png_bytes())

    assert result.is_safe is False
    assert "face_detected" in result.reject_reasons


@pytest.mark.asyncio
@respx.mock
async def test_assigns_object_ids_when_provider_omits_them():
    payload = {
        "is_safe": True,
        "reject_reasons": [],
        "scene_summary": "scene",
        "objects": [
            {"label": "apple", "bbox": [0.1, 0.1, 0.1, 0.1]},
            {"label": "pear", "bbox": [0.2, 0.2, 0.1, 0.1]},
        ],
    }
    respx.post(QWEN_URL).mock(return_value=httpx.Response(200, json=_build_response(payload)))

    adapter = _build_adapter()
    result = await adapter.analyze_image(safe_png_bytes())

    ids = [o.id for o in result.objects]
    assert len(set(ids)) == 2
    assert all(i for i in ids)


@pytest.mark.asyncio
@respx.mock
async def test_http_500_raises_upstream_failure():
    respx.post(QWEN_URL).mock(return_value=httpx.Response(500, text="server error"))

    adapter = _build_adapter()
    with pytest.raises(UpstreamFailureError) as exc_info:
        await adapter.analyze_image(safe_png_bytes())
    assert exc_info.value.provider == "qwen"


@pytest.mark.asyncio
@respx.mock
async def test_timeout_raises_upstream_timeout():
    respx.post(QWEN_URL).mock(side_effect=httpx.TimeoutException("timed out"))

    adapter = _build_adapter()
    with pytest.raises(UpstreamTimeoutError) as exc_info:
        await adapter.analyze_image(safe_png_bytes())
    assert exc_info.value.provider == "qwen"


@pytest.mark.asyncio
@respx.mock
async def test_invalid_json_in_response_raises_upstream_failure():
    bad_envelope = {
        "choices": [{"message": {"content": "not-json-at-all"}, "finish_reason": "stop"}]
    }
    respx.post(QWEN_URL).mock(return_value=httpx.Response(200, json=bad_envelope))

    adapter = _build_adapter()
    with pytest.raises(UpstreamFailureError) as exc_info:
        await adapter.analyze_image(safe_png_bytes())
    assert exc_info.value.provider == "qwen"


@pytest.mark.asyncio
@respx.mock
async def test_request_includes_authorization_header_and_image_data_url():
    captured: dict = {}

    def _capture(request: httpx.Request) -> httpx.Response:
        captured["headers"] = dict(request.headers)
        captured["body"] = json.loads(request.content.decode())
        payload = {
            "is_safe": True,
            "reject_reasons": [],
            "scene_summary": "ok",
            "objects": [],
        }
        return httpx.Response(200, json=_build_response(payload))

    respx.post(QWEN_URL).mock(side_effect=_capture)

    adapter = _build_adapter()
    await adapter.analyze_image(safe_png_bytes())

    assert captured["headers"].get("authorization") == "Bearer sk-qwen"
    assert captured["body"]["model"] == "qwen-vl-max-latest"
    user_msg = captured["body"]["messages"][1]
    image_part = next(p for p in user_msg["content"] if p["type"] == "image_url")
    assert image_part["image_url"]["url"].startswith("data:image/")
    assert "base64," in image_part["image_url"]["url"]
