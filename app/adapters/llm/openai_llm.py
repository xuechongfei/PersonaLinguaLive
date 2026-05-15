"""OpenAI Chat Completions adapter for text-generation LLM."""
from __future__ import annotations

import json
from collections.abc import AsyncGenerator

import httpx
import structlog

from app.errors import UpstreamFailureError, UpstreamTimeoutError

log = structlog.get_logger("pll.adapter.openai_llm")


class OpenAILLMAdapter:
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        timeout_s: float,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout_s = timeout_s

    async def generate(
        self,
        messages: list[dict],
        *,
        temperature: float = 0.7,
    ) -> str:
        url = f"{self._base_url}/chat/completions"
        body = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        log.info("openai.llm.call", model=self._model, messages=len(messages), temperature=temperature)

        try:
            async with httpx.AsyncClient(timeout=self._timeout_s) as client:
                resp = await client.post(url, json=body, headers=headers)
        except httpx.TimeoutException as exc:
            log.warning("openai.llm.timeout", error=str(exc))
            raise UpstreamTimeoutError(provider="openai") from exc
        except httpx.HTTPError as exc:
            log.warning("openai.llm.http_error", error=str(exc))
            raise UpstreamFailureError(provider="openai", message=str(exc)) from exc

        if resp.status_code >= 400:
            log.warning("openai.llm.http_status", status=resp.status_code, body=resp.text[:500])
            raise UpstreamFailureError(
                provider="openai",
                message=f"openai returned {resp.status_code}",
            )

        try:
            envelope = resp.json()
            content = envelope["choices"][0]["message"]["content"]
            log.info("openai.llm.ok", len=len(content))
            return content
        except (KeyError, IndexError, ValueError) as exc:
            log.warning("openai.llm.parse_error", error=str(exc))
            raise UpstreamFailureError(provider="openai", message="invalid response from upstream") from exc

    async def generate_stream(
        self,
        messages: list[dict],
        *,
        temperature: float = 0.7,
    ) -> AsyncGenerator[str, None]:
        url = f"{self._base_url}/chat/completions"
        body = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
            "stream": True,
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout_s) as client:
                async with client.stream("POST", url, json=body, headers=headers) as resp:
                    if resp.status_code >= 400:
                        log.warning("openai.llm.stream_http_status", status=resp.status_code)
                        raise UpstreamFailureError(
                            provider="openai",
                            message=f"openai returned {resp.status_code}",
                        )
                    async for line in resp.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        payload = line.removeprefix("data: ").strip()
                        if payload == "[DONE]":
                            return
                        try:
                            chunk = json.loads(payload)
                            delta = chunk.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content")
                            if content:
                                yield content
                        except (json.JSONDecodeError, KeyError, IndexError):
                            continue
        except httpx.TimeoutException as exc:
            log.warning("openai.llm.stream_timeout", error=str(exc))
            raise UpstreamTimeoutError(provider="openai") from exc
        except httpx.HTTPError as exc:
            log.warning("openai.llm.stream_http_error", error=str(exc))
            raise UpstreamFailureError(provider="openai", message=str(exc)) from exc
