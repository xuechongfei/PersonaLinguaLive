from __future__ import annotations
import base64

import httpx
import pytest
import respx

from app.errors import UpstreamFailureError, UpstreamTimeoutError


def _ok(b64: str) -> dict:
    return {"created": 0, "data": [{"b64_json": b64}]}


@pytest.mark.asyncio
@respx.mock
async def test_text_to_image_returns_decoded_bytes():
    from app.adapters.imagegen.openai import OpenAIImageGenAdapter
    payload = b"\x89PNG\r\n\x1a\nHELLO"
    b64 = base64.b64encode(payload).decode()
    respx.post("https://api.openai.com/v1/images/generations").mock(
        return_value=httpx.Response(200, json=_ok(b64))
    )
    adapter = OpenAIImageGenAdapter(
        api_key="sk-test", base_url="https://api.openai.com/v1",
        model="gpt-image-1", timeout_s=10.0,
    )
    result = await adapter.text_to_image("a cat")
    assert result.image_bytes == payload


@pytest.mark.asyncio
@respx.mock
async def test_text_to_image_sends_model_and_prompt():
    from app.adapters.imagegen.openai import OpenAIImageGenAdapter
    route = respx.post("https://api.openai.com/v1/images/generations").mock(
        return_value=httpx.Response(200, json=_ok(base64.b64encode(b"\x89PNG").decode()))
    )
    adapter = OpenAIImageGenAdapter(
        api_key="sk-test", base_url="https://api.openai.com/v1",
        model="gpt-image-1", timeout_s=10.0,
    )
    await adapter.text_to_image("a cat", size="512x512")
    body = route.calls.last.request.read().decode()
    assert "gpt-image-1" in body and "a cat" in body and "512x512" in body


@pytest.mark.asyncio
@respx.mock
async def test_http_500_raises():
    from app.adapters.imagegen.openai import OpenAIImageGenAdapter
    respx.post("https://api.openai.com/v1/images/generations").mock(
        return_value=httpx.Response(500, text="boom")
    )
    adapter = OpenAIImageGenAdapter(
        api_key="sk-test", base_url="https://api.openai.com/v1",
        model="gpt-image-1", timeout_s=10.0,
    )
    with pytest.raises(UpstreamFailureError) as ei:
        await adapter.text_to_image("a cat")
    assert ei.value.provider == "openai"


@pytest.mark.asyncio
@respx.mock
async def test_timeout_raises():
    from app.adapters.imagegen.openai import OpenAIImageGenAdapter
    respx.post("https://api.openai.com/v1/images/generations").mock(
        side_effect=httpx.TimeoutException("slow")
    )
    adapter = OpenAIImageGenAdapter(
        api_key="sk-test", base_url="https://api.openai.com/v1",
        model="gpt-image-1", timeout_s=0.1,
    )
    with pytest.raises(UpstreamTimeoutError):
        await adapter.text_to_image("a cat")
