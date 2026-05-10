"""Tests for OpenAILLMAdapter (httpx mocked via respx)."""
from __future__ import annotations

import json

import httpx
import pytest
import respx

from app.errors import UpstreamFailureError, UpstreamTimeoutError


def _build_single_response(text: str) -> dict:
    return {
        "id": "chatcmpl-x",
        "object": "chat.completion",
        "created": 0,
        "model": "gpt-4o-mini",
        "choices": [{"index": 0, "message": {"role": "assistant", "content": text}, "finish_reason": "stop"}],
    }


def _build_stream_chunk(content: str | None) -> str:
    data = {"choices": [{"index": 0, "delta": {"content": content} if content else {}}]}
    return f"data: {json.dumps(data)}\n\n"


@pytest.mark.asyncio
@respx.mock
async def test_single_response_returns_text():
    from app.adapters.llm.openai_llm import OpenAILLMAdapter

    respx.post("https://api.openai.com/v1/chat/completions").mock(
        return_value=httpx.Response(200, json=_build_single_response("Hello world!"))
    )

    adapter = OpenAILLMAdapter(api_key="sk-test", base_url="https://api.openai.com/v1", model="gpt-4o-mini", timeout_s=10.0)
    result = await adapter.generate([{"role": "user", "content": "Say hi"}])
    assert result == "Hello world!"


@pytest.mark.asyncio
@respx.mock
async def test_streaming_yields_tokens_in_order():
    from app.adapters.llm.openai_llm import OpenAILLMAdapter

    chunks = [_build_stream_chunk("Hello"), _build_stream_chunk(" "), _build_stream_chunk("world"), _build_stream_chunk("!"), _build_stream_chunk(None), "data: [DONE]\n\n"]
    body = "".join(chunks)

    respx.post("https://api.openai.com/v1/chat/completions").mock(
        return_value=httpx.Response(200, text=body)
    )

    adapter = OpenAILLMAdapter(api_key="sk-test", base_url="https://api.openai.com/v1", model="gpt-4o-mini", timeout_s=10.0)
    tokens = []
    async for token in adapter.generate_stream([{"role": "user", "content": "Say hi"}]):
        tokens.append(token)
    assert "".join(tokens) == "Hello world!"


@pytest.mark.asyncio
@respx.mock
async def test_http_500_raises_upstream_failure():
    from app.adapters.llm.openai_llm import OpenAILLMAdapter

    respx.post("https://api.openai.com/v1/chat/completions").mock(
        return_value=httpx.Response(500, text="server error")
    )

    adapter = OpenAILLMAdapter(api_key="sk-test", base_url="https://api.openai.com/v1", model="gpt-4o-mini", timeout_s=10.0)
    with pytest.raises(UpstreamFailureError):
        await adapter.generate([{"role": "user", "content": "Hi"}])


@pytest.mark.asyncio
@respx.mock
async def test_timeout_raises_upstream_timeout():
    from app.adapters.llm.openai_llm import OpenAILLMAdapter

    respx.post("https://api.openai.com/v1/chat/completions").mock(
        side_effect=httpx.TimeoutException("timed out")
    )

    adapter = OpenAILLMAdapter(api_key="sk-test", base_url="https://api.openai.com/v1", model="gpt-4o-mini", timeout_s=10.0)
    with pytest.raises(UpstreamTimeoutError):
        await adapter.generate([{"role": "user", "content": "Hi"}])


@pytest.mark.asyncio
@respx.mock
async def test_stream_http_500_raises_upstream_failure():
    from app.adapters.llm.openai_llm import OpenAILLMAdapter

    respx.post("https://api.openai.com/v1/chat/completions").mock(
        return_value=httpx.Response(500, text="server error")
    )

    adapter = OpenAILLMAdapter(api_key="sk-test", base_url="https://api.openai.com/v1", model="gpt-4o-mini", timeout_s=10.0)
    with pytest.raises(UpstreamFailureError):
        async for _ in adapter.generate_stream([{"role": "user", "content": "Hi"}]):
            pass


@pytest.mark.asyncio
@respx.mock
async def test_request_includes_authorization_header():
    from app.adapters.llm.openai_llm import OpenAILLMAdapter

    captured: dict = {}

    def _capture(request: httpx.Request) -> httpx.Response:
        captured["headers"] = dict(request.headers)
        captured["body"] = json.loads(request.content.decode())
        return httpx.Response(200, json=_build_single_response("ok"))

    respx.post("https://api.openai.com/v1/chat/completions").mock(side_effect=_capture)

    adapter = OpenAILLMAdapter(api_key="sk-secret", base_url="https://api.openai.com/v1", model="gpt-4o-mini", timeout_s=10.0)
    await adapter.generate([{"role": "user", "content": "Hi"}])

    assert captured["headers"].get("authorization") == "Bearer sk-secret"
    assert captured["body"]["model"] == "gpt-4o-mini"
