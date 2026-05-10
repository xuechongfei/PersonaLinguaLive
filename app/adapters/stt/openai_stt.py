"""OpenAI STT adapter using POST /v1/audio/transcriptions."""
from __future__ import annotations

import httpx
import structlog

from app.errors import UpstreamFailureError, UpstreamTimeoutError

log = structlog.get_logger("pll.adapter.openai_stt")


class OpenAISTTAdapter:
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

    async def transcribe(
        self,
        audio_bytes: bytes,
        *,
        language: str | None = None,
    ) -> str:
        url = f"{self._base_url}/audio/transcriptions"
        files = {"file": ("audio.wav", audio_bytes, "audio/wav")}
        data: dict = {"model": self._model}
        if language:
            data["language"] = language
        headers = {"Authorization": f"Bearer {self._api_key}"}

        try:
            async with httpx.AsyncClient(timeout=self._timeout_s) as client:
                resp = await client.post(url, files=files, data=data, headers=headers)
        except httpx.TimeoutException as exc:
            log.warning("openai.stt.timeout", error=str(exc))
            raise UpstreamTimeoutError(provider="openai") from exc
        except httpx.HTTPError as exc:
            log.warning("openai.stt.http_error", error=str(exc))
            raise UpstreamFailureError(provider="openai", message=str(exc)) from exc

        if resp.status_code >= 400:
            log.warning("openai.stt.http_status", status=resp.status_code, body=resp.text[:500])
            raise UpstreamFailureError(
                provider="openai",
                message=f"openai returned {resp.status_code}",
            )

        try:
            body = resp.json()
            return body["text"]
        except (KeyError, ValueError) as exc:
            log.warning("openai.stt.parse_error", error=str(exc))
            raise UpstreamFailureError(provider="openai", message="invalid response from upstream") from exc
