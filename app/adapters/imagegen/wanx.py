"""Tongyi Wanxiang (通义万象) adapter via DashScope async image synthesis API."""
from __future__ import annotations

import asyncio

import httpx
import structlog

from app.adapters.imagegen.base import ImageGenAdapter, ImageGenResult
from app.errors import UpstreamFailureError, UpstreamTimeoutError

log = structlog.get_logger("pll.adapter.wanx_imagegen")

_TASK_POLL_URL = "https://dashscope.aliyuncs.com/api/v1/tasks"


class WanxImageGenAdapter(ImageGenAdapter):
    def __init__(self, *, api_key: str, base_url: str, model: str, timeout_s: float) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout_s = timeout_s

    async def text_to_image(self, prompt, *, size="1024x1024", reference_image=None):
        log.info("wanx.imagegen.text_to_image.call", model=self._model, size=size,
                 prompt_len=len(prompt))
        return await self._generate(prompt, size)

    async def image_to_image(self, image_bytes, prompt, *, size="1024x1024", strength=0.7):
        log.info("wanx.imagegen.image_to_image.call", model=self._model, size=size,
                 prompt_len=len(prompt), src_bytes=len(image_bytes))
        enhanced_prompt = (
            f"{prompt}\n\n"
            f"Reference style and composition from the original scene. "
            f"Maintain the same layout and spatial arrangement. "
            f"Cartoon illustration style, warm colors, clean lines."
        )
        return await self._generate(enhanced_prompt, size)

    async def _generate(self, prompt: str, size: str) -> ImageGenResult:
        url = f"{self._base_url}/text2image/image-synthesis"
        body = {
            "model": self._model,
            "input": {"prompt": prompt, "n": 1, "size": size.replace("x", "*")},
            "parameters": {"style": "auto", "watermark": False},
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "X-DashScope-Async": "enable",
        }

        # Submit with retry for rate limits (free tier: 1-2 QPS)
        for attempt in range(4):
            try:
                async with httpx.AsyncClient(timeout=self._timeout_s) as client:
                    resp = await client.post(url, json=body, headers=headers)
            except httpx.TimeoutException as exc:
                log.warning("wanx.imagegen.timeout", error=str(exc))
                raise UpstreamTimeoutError(provider="wanx") from exc
            except httpx.HTTPError as exc:
                log.warning("wanx.imagegen.http_error", error=str(exc))
                raise UpstreamFailureError(provider="wanx", message=str(exc)) from exc

            if resp.status_code == 429:
                delay = 2 ** attempt  # 1s, 2s, 4s, 8s
                log.info("wanx.imagegen.rate_limited", attempt=attempt + 1, retry_in=delay)
                await asyncio.sleep(delay)
                continue

            if resp.status_code >= 400:
                log.warning("wanx.imagegen.http_status", status=resp.status_code,
                            body=resp.text[:500])
                raise UpstreamFailureError(
                    provider="wanx", message=f"wanx returned {resp.status_code}"
                )

            data = resp.json()
            output = data.get("output", {})
            task_status = output.get("task_status", "")
            task_id = output.get("task_id", "")

            # Handle sync success (if account supports it)
            if task_status == "SUCCEEDED":
                return await self._extract_result(output)

            # Async: poll until complete
            if task_status in ("PENDING", "RUNNING") and task_id:
                log.info("wanx.imagegen.async_task", task_id=task_id)
                data = await self._poll_task(task_id)
                output = data.get("output", {})
            else:
                raise UpstreamFailureError(
                    provider="wanx",
                    message=f"unexpected task status: {task_status}",
                )

            return await self._extract_result(output)

        raise UpstreamFailureError(
            provider="wanx", message="rate limit exceeded after 4 retries"
        )

    async def _extract_result(self, output: dict) -> ImageGenResult:
        task_status = output.get("task_status", "FAILED")
        if task_status != "SUCCEEDED":
            log.warning("wanx.imagegen.task_failed", task_status=task_status,
                        message=output.get("message", ""))
            raise UpstreamFailureError(
                provider="wanx",
                message=f"image generation failed: {task_status}",
            )

        results = output.get("results", [])
        if not results or not results[0].get("url"):
            raise UpstreamFailureError(
                provider="wanx", message="response missing image url"
            )

        image_url = results[0]["url"]
        image_bytes = await self._download_image(image_url)
        log.info("wanx.imagegen.ok", bytes=len(image_bytes))
        return ImageGenResult(image_bytes, "image/png")

    async def _download_image(self, url: str) -> bytes:
        try:
            async with httpx.AsyncClient(timeout=self._timeout_s) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                return resp.content
        except httpx.TimeoutException as exc:
            raise UpstreamTimeoutError(provider="wanx") from exc
        except httpx.HTTPError as exc:
            raise UpstreamFailureError(provider="wanx", message=str(exc)) from exc

    async def _poll_task(self, task_id: str) -> dict:
        url = f"{_TASK_POLL_URL}/{task_id}"
        headers = {"Authorization": f"Bearer {self._api_key}"}

        for attempt in range(30):  # max 30 * 2s = 60s
            await asyncio.sleep(2)
            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.get(url, headers=headers)
            except (httpx.TimeoutException, httpx.HTTPError):
                continue

            if resp.status_code >= 400:
                log.warning("wanx.imagegen.poll_error", status=resp.status_code,
                            attempt=attempt + 1)
                continue

            data = resp.json()
            status = data.get("output", {}).get("task_status", "")
            if status == "SUCCEEDED":
                return data
            if status == "FAILED":
                raise UpstreamFailureError(
                    provider="wanx",
                    message=f"async task {task_id} failed",
                )

        raise UpstreamTimeoutError(provider="wanx")
