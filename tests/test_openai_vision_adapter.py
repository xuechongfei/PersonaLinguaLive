"""Tests for OpenAIVisionAdapter (httpx mocked via respx)."""
from __future__ import annotations

import json

import httpx
import pytest
import respx

from app.errors import UpstreamFailureError, UpstreamTimeoutError
from tests.fixtures.images import safe_png_bytes


def _build_response(json_payload: dict) -> dict:
    """Wrap a vision JSON object in the OpenAI chat-completions envelope."""
    return {
        "id": "chatcmpl-x",
        "object": "chat.completion",
        "created": 0,
        "model": "gpt-4o",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": json.dumps(json_payload)},
                "finish_reason": "stop",
            }
        ],
    }


@pytest.mark.asyncio
@respx.mock
async def test_parses_safe_response_into_vision_result():
    from app.adapters.vision.openai_vision import OpenAIVisionAdapter

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
            {
                "label": "saucepan",
                "bbox": [0.1, 0.3, 0.2, 0.25],
                "persona_seed": "old chef",
            },
        ],
    }
    respx.post("https://api.openai.com/v1/chat/completions").mock(
        return_value=httpx.Response(200, json=_build_response(payload))
    )

    adapter = OpenAIVisionAdapter(
        api_key="sk-test",
        base_url="https://api.openai.com/v1",
        model="gpt-4o",
        timeout_s=10.0,
    )
    result = await adapter.analyze_image(safe_png_bytes())

    assert result.is_safe is True
    assert result.scene_summary == "A modern kitchen."
    assert len(result.objects) == 2
    assert result.objects[0].label == "cupcake"
    assert result.objects[0].bbox.x == 0.4


@pytest.mark.asyncio
@respx.mock
async def test_parses_unsafe_response():
    from app.adapters.vision.openai_vision import OpenAIVisionAdapter

    payload = {
        "is_safe": False,
        "reject_reasons": ["face_detected"],
        "scene_summary": "",
        "objects": [],
    }
    respx.post("https://api.openai.com/v1/chat/completions").mock(
        return_value=httpx.Response(200, json=_build_response(payload))
    )

    adapter = OpenAIVisionAdapter(api_key="sk-test", base_url="https://api.openai.com/v1", model="gpt-4o", timeout_s=10.0)
    result = await adapter.analyze_image(safe_png_bytes())

    assert result.is_safe is False
    assert "face_detected" in result.reject_reasons


@pytest.mark.asyncio
@respx.mock
async def test_assigns_object_ids_when_provider_omits_them():
    from app.adapters.vision.openai_vision import OpenAIVisionAdapter

    payload = {
        "is_safe": True,
        "reject_reasons": [],
        "scene_summary": "scene",
        "objects": [
            {"label": "apple", "bbox": [0.1, 0.1, 0.1, 0.1], "persona_seed": "x"},
            {"label": "pear", "bbox": [0.2, 0.2, 0.1, 0.1], "persona_seed": "y"},
        ],
    }
    respx.post("https://api.openai.com/v1/chat/completions").mock(
        return_value=httpx.Response(200, json=_build_response(payload))
    )

    adapter = OpenAIVisionAdapter(api_key="sk-test", base_url="https://api.openai.com/v1", model="gpt-4o", timeout_s=10.0)
    result = await adapter.analyze_image(safe_png_bytes())

    ids = [o.id for o in result.objects]
    assert len(set(ids)) == 2
    assert all(i for i in ids)  # 非空


@pytest.mark.asyncio
@respx.mock
async def test_http_500_raises_upstream_failure():
    from app.adapters.vision.openai_vision import OpenAIVisionAdapter

    respx.post("https://api.openai.com/v1/chat/completions").mock(
        return_value=httpx.Response(500, text="server error")
    )

    adapter = OpenAIVisionAdapter(api_key="sk-test", base_url="https://api.openai.com/v1", model="gpt-4o", timeout_s=10.0)
    with pytest.raises(UpstreamFailureError):
        await adapter.analyze_image(safe_png_bytes())


@pytest.mark.asyncio
@respx.mock
async def test_timeout_raises_upstream_timeout():
    from app.adapters.vision.openai_vision import OpenAIVisionAdapter

    respx.post("https://api.openai.com/v1/chat/completions").mock(
        side_effect=httpx.TimeoutException("timed out")
    )

    adapter = OpenAIVisionAdapter(api_key="sk-test", base_url="https://api.openai.com/v1", model="gpt-4o", timeout_s=10.0)
    with pytest.raises(UpstreamTimeoutError):
        await adapter.analyze_image(safe_png_bytes())


@pytest.mark.asyncio
@respx.mock
async def test_invalid_json_in_response_raises_upstream_failure():
    from app.adapters.vision.openai_vision import OpenAIVisionAdapter

    bad_envelope = {
        "choices": [{"message": {"content": "not-json-at-all"}, "finish_reason": "stop"}]
    }
    respx.post("https://api.openai.com/v1/chat/completions").mock(
        return_value=httpx.Response(200, json=bad_envelope)
    )

    adapter = OpenAIVisionAdapter(api_key="sk-test", base_url="https://api.openai.com/v1", model="gpt-4o", timeout_s=10.0)
    with pytest.raises(UpstreamFailureError):
        await adapter.analyze_image(safe_png_bytes())


@pytest.mark.asyncio
@respx.mock
async def test_request_includes_authorization_header_and_image_data_url():
    from app.adapters.vision.openai_vision import OpenAIVisionAdapter

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

    respx.post("https://api.openai.com/v1/chat/completions").mock(side_effect=_capture)

    adapter = OpenAIVisionAdapter(api_key="sk-secret", base_url="https://api.openai.com/v1", model="gpt-4o", timeout_s=10.0)
    await adapter.analyze_image(safe_png_bytes())

    assert captured["headers"].get("authorization") == "Bearer sk-secret"
    assert captured["body"]["model"] == "gpt-4o"
    user_msg = captured["body"]["messages"][1]
    image_part = next(p for p in user_msg["content"] if p["type"] == "image_url")
    assert image_part["image_url"]["url"].startswith("data:image/")
    assert "base64," in image_part["image_url"]["url"]
