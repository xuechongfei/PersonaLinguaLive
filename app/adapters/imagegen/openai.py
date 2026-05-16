"""OpenAI Image Generation adapter (DALL-E / gpt-image-1 / CogView / etc.)."""
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
        log.info("openai.imagegen.text_to_image.call", model=self._model, size=size,
                 prompt_len=len(prompt))
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
        log.info("openai.imagegen.image_to_image.call", model=self._model, size=size,
                 prompt_len=len(prompt), src_bytes=len(image_bytes))
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

        # If /images/edits is not available (e.g. Zhipu), fall back to text_to_image
        if resp.status_code in (404, 405):
            log.info("openai.imagegen.edit_not_supported, fallback to text_to_image")
            return await self.text_to_image(prompt, size=size)

        if resp.status_code >= 400:
            log.warning("openai.imagegen.edit.http_status", status=resp.status_code,
                        body=resp.text[:500])
            raise UpstreamFailureError(provider="openai",
                                       message=f"openai returned {resp.status_code}")

        return await self._parse_data(resp.json())

    async def _post_generations(self, body: dict) -> ImageGenResult:
        url = f"{self._base_url}/images/generations"
        headers = {"Authorization": f"Bearer {self._api_key}",
                   "Content-Type": "application/json"}
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
            log.warning("openai.imagegen.http_status", status=resp.status_code,
                        body=resp.text[:500])
            raise UpstreamFailureError(provider="openai",
                                       message=f"openai returned {resp.status_code}")
        return await self._parse_data(resp.json())

    async def _parse_data(self, envelope: dict) -> ImageGenResult:
        """Parse response supporting both b64_json and url formats."""
        try:
            item = envelope["data"][0]
        except (KeyError, IndexError) as exc:
            raise UpstreamFailureError(provider="openai",
                                       message="invalid response shape") from exc

        # b64_json format (OpenAI)
        if "b64_json" in item:
            try:
                image_bytes = base64.b64decode(item["b64_json"])
                return ImageGenResult(image_bytes, "image/png")
            except (ValueError, base64.binascii.Error) as exc:
                raise UpstreamFailureError(provider="openai",
                                           message="invalid base64 in response") from exc

        # url format (Zhipu CogView, etc.) — download the image
        if "url" in item:
            image_bytes = await self._download(item["url"])
            return ImageGenResult(image_bytes, "image/png")

        raise UpstreamFailureError(provider="openai",
                                   message="response missing b64_json or url")

    async def _download(self, url: str) -> bytes:
        try:
            async with httpx.AsyncClient(timeout=self._timeout_s) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                return resp.content
        except httpx.TimeoutException as exc:
            raise UpstreamTimeoutError(provider="openai") from exc
        except httpx.HTTPError as exc:
            raise UpstreamFailureError(provider="openai", message=str(exc)) from exc
