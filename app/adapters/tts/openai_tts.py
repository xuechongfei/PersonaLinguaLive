"""OpenAI TTS adapter using POST /v1/audio/speech."""
from __future__ import annotations

import httpx
import structlog

from app.errors import UpstreamFailureError, UpstreamTimeoutError

log = structlog.get_logger("pll.adapter.openai_tts")


class OpenAITTSAdapter:
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

    async def synthesize(
        self,
        text: str,
        *,
        voice: str = "alloy",
    ) -> bytes:
        url = f"{self._base_url}/audio/speech"
        body = {
            "model": self._model,
            "input": text,
            "voice": voice,
            "response_format": "mp3",
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        log.info("openai.tts.call", model=self._model, voice=voice, text_len=len(text))

        try:
            async with httpx.AsyncClient(timeout=self._timeout_s) as client:
                resp = await client.post(url, json=body, headers=headers)
        except httpx.TimeoutException as exc:
            log.warning("openai.tts.timeout", error=str(exc))
            raise UpstreamTimeoutError(provider="openai") from exc
        except httpx.HTTPError as exc:
            log.warning("openai.tts.http_error", error=str(exc))
            raise UpstreamFailureError(provider="openai", message=str(exc)) from exc

        if resp.status_code >= 400:
            log.warning("openai.tts.http_status", status=resp.status_code, body=resp.text[:500])
            raise UpstreamFailureError(
                provider="openai",
                message=f"openai returned {resp.status_code}",
            )

        audio = resp.content
        log.info("openai.tts.ok", bytes=len(audio))
        return audio
