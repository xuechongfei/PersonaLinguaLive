"""OpenAI Image Generation adapter (DALL-E / gpt-image-1)."""
from __future__ import annotations

import base64

import httpx
import structlog

from app.adapters.imagegen.base import ImageGenAdapter, ImageGenResult
from app.errors import UpstreamFailureError, UpstreamTimeoutError

log = structlog.get_logger("pll.adapter.openai_imagegen")


class OpenAIImageGenAdapter(ImageGenAdapter):
    def __init__(self, *, api_key: str, base_url: str, model: str, timeout_s: float) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout_s = timeout_s

    async def text_to_image(self, prompt, *, size="1024x1024", reference_image=None):
        log.info("openai.imagegen.text_to_image.call", model=self._model, size=size, prompt_len=len(prompt))
        body = {
            "model": self._model,
            "prompt": prompt,
            "size": size,
            "n": 1,
            "response_format": "b64_json",
        }
        result = await self._post_generations(body)
        log.info("openai.imagegen.text_to_image.ok", bytes=len(result.image_bytes))
        return result

    async def image_to_image(self, image_bytes, prompt, *, size="1024x1024", strength=0.7):
        log.info("openai.imagegen.image_to_image.call", model=self._model, size=size, prompt_len=len(prompt), src_bytes=len(image_bytes))
        url = f"{self._base_url}/images/edits"
        headers = {"Authorization": f"Bearer {self._api_key}"}
        files = {"image": ("input.png", image_bytes, "image/png")}
        data = {
            "model": self._model,
            "prompt": prompt,
            "size": size,
            "n": "1",
            "response_format": "b64_json",
        }
        try:
            async with httpx.AsyncClient(timeout=self._timeout_s) as client:
                resp = await client.post(url, headers=headers, files=files, data=data)
        except httpx.TimeoutException as exc:
            log.warning("openai.imagegen.edit.timeout", error=str(exc))
            raise UpstreamTimeoutError(provider="openai") from exc
        except httpx.HTTPError as exc:
            log.warning("openai.imagegen.edit.http_error", error=str(exc))
            raise UpstreamFailureError(provider="openai", message=str(exc)) from exc
        if resp.status_code >= 400:
            log.warning("openai.imagegen.edit.http_status", status=resp.status_code, body=resp.text[:500])
            raise UpstreamFailureError(provider="openai", message=f"openai returned {resp.status_code}")
        try:
            envelope = resp.json()
            decoded = base64.b64decode(envelope["data"][0]["b64_json"])
        except (KeyError, IndexError, ValueError) as exc:
            log.warning("openai.imagegen.edit.parse_error", error=str(exc))
            raise UpstreamFailureError(provider="openai", message="invalid response") from exc
        return ImageGenResult(decoded, "image/png")

    async def _post_generations(self, body: dict) -> ImageGenResult:
        url = f"{self._base_url}/images/generations"
        headers = {"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"}
        try:
            async with httpx.AsyncClient(timeout=self._timeout_s) as client:
                resp = await client.post(url, json=body, headers=headers)
        except httpx.TimeoutException as exc:
            log.warning("openai.imagegen.timeout", error=str(exc))
            raise UpstreamTimeoutError(provider="openai") from exc
        except httpx.HTTPError as exc:
            log.warning("openai.imagegen.http_error", error=str(exc))
            raise UpstreamFailureError(provider="openai", message=str(exc)) from exc
        if resp.status_code >= 400:
            log.warning("openai.imagegen.http_status", status=resp.status_code, body=resp.text[:500])
            raise UpstreamFailureError(provider="openai", message=f"openai returned {resp.status_code}")
        try:
            envelope = resp.json()
            decoded = base64.b64decode(envelope["data"][0]["b64_json"])
        except (KeyError, IndexError, ValueError) as exc:
            log.warning("openai.imagegen.parse_error", error=str(exc))
            raise UpstreamFailureError(provider="openai", message="invalid response") from exc
        return ImageGenResult(decoded, "image/png")
