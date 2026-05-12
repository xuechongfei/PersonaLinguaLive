"""Qwen-VL adapter via DashScope compatible-mode (OpenAI-compatible chat completions)."""
from __future__ import annotations

import json

import httpx
import structlog

from app.adapters.vision.base import VisionIntent
from app.adapters.vision.openai_vision import _payload_to_result, _to_data_url
from app.errors import UpstreamFailureError, UpstreamTimeoutError
from app.prompts.vision_safety import build_vision_safety_messages
from app.schemas.vision import VisionResult

log = structlog.get_logger("pll.adapter.qwen_vision")

_PROVIDER = "qwen"


class QwenVisionAdapter:
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

    async def analyze_image(
        self,
        image_bytes: bytes,
        *,
        intent: VisionIntent = "safety_and_objects",
    ) -> VisionResult:
        url = f"{self._base_url}/chat/completions"
        messages = build_vision_safety_messages(image_data_url=_to_data_url(image_bytes))
        body = {
            "model": self._model,
            "messages": messages,
            "response_format": {"type": "json_object"},
            "temperature": 0.0,
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout_s) as client:
                resp = await client.post(url, json=body, headers=headers)
        except httpx.TimeoutException as exc:
            log.warning("qwen.vision.timeout", error=str(exc))
            raise UpstreamTimeoutError(provider=_PROVIDER) from exc
        except httpx.HTTPError as exc:
            log.warning("qwen.vision.http_error", error=str(exc))
            raise UpstreamFailureError(provider=_PROVIDER, message=str(exc)) from exc

        if resp.status_code >= 400:
            log.warning("qwen.vision.http_status", status=resp.status_code, body=resp.text[:500])
            raise UpstreamFailureError(
                provider=_PROVIDER,
                message=f"qwen returned {resp.status_code}",
            )

        try:
            envelope = resp.json()
            content_str = envelope["choices"][0]["message"]["content"]
            payload = json.loads(content_str)
        except (KeyError, IndexError, ValueError) as exc:
            log.warning("qwen.vision.parse_error", error=str(exc))
            raise UpstreamFailureError(
                provider=_PROVIDER, message="invalid JSON from upstream"
            ) from exc

        return _payload_to_result(payload)
