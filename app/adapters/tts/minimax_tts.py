"""MiniMax T2A v2 adapter (speech-02-hd).

Differences from OpenAI TTS:
  - Response is a JSON envelope; audio bytes come back hex-encoded under data.audio.
  - Application-level errors are signaled via base_resp.status_code (0 = success).
"""
from __future__ import annotations

import httpx
import structlog

from app.errors import UpstreamFailureError, UpstreamTimeoutError

log = structlog.get_logger("pll.adapter.minimax_tts")

_PROVIDER = "minimax"

# The legacy default voice from the OpenAI adapter; remap to the MiniMax default.
_LEGACY_VOICE_ALIASES = {"alloy", "", None}


class MiniMaxTTSAdapter:
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        default_voice: str,
        timeout_s: float,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._default_voice = default_voice
        self._timeout_s = timeout_s

    async def synthesize(
        self,
        text: str,
        *,
        voice: str = "alloy",
    ) -> bytes:
        voice_id = voice if voice not in _LEGACY_VOICE_ALIASES else self._default_voice

        url = f"{self._base_url}/t2a_v2"
        body = {
            "model": self._model,
            "text": text,
            "stream": False,
            "voice_setting": {
                "voice_id": voice_id,
                "speed": 1.0,
                "vol": 1.0,
                "pitch": 0,
            },
            "audio_setting": {
                "sample_rate": 32000,
                "bitrate": 128000,
                "format": "mp3",
                "channel": 1,
            },
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        log.info("minimax.tts.call", model=self._model, voice_id=voice_id, text_len=len(text))

        try:
            async with httpx.AsyncClient(timeout=self._timeout_s) as client:
                resp = await client.post(url, json=body, headers=headers)
        except httpx.TimeoutException as exc:
            log.warning("minimax.tts.timeout", error=str(exc))
            raise UpstreamTimeoutError(provider=_PROVIDER) from exc
        except httpx.HTTPError as exc:
            log.warning("minimax.tts.http_error", error=str(exc))
            raise UpstreamFailureError(provider=_PROVIDER, message=str(exc)) from exc

        if resp.status_code >= 400:
            log.warning("minimax.tts.http_status", status=resp.status_code, body=resp.text[:500])
            raise UpstreamFailureError(
                provider=_PROVIDER,
                message=f"minimax returned {resp.status_code}",
            )

        try:
            envelope = resp.json()
        except ValueError as exc:
            log.warning("minimax.tts.invalid_json", error=str(exc))
            raise UpstreamFailureError(
                provider=_PROVIDER, message="invalid JSON from upstream"
            ) from exc

        base_resp = envelope.get("base_resp") or {}
        status_code = base_resp.get("status_code")
        if status_code not in (0, None):
            msg = base_resp.get("status_msg") or "unknown"
            log.warning("minimax.tts.app_error", status_code=status_code, status_msg=msg)
            raise UpstreamFailureError(
                provider=_PROVIDER,
                message=f"minimax application error {status_code}: {msg}",
            )

        audio_hex = (envelope.get("data") or {}).get("audio")
        if not audio_hex:
            log.warning("minimax.tts.missing_audio", envelope_keys=list(envelope.keys()))
            raise UpstreamFailureError(
                provider=_PROVIDER, message="response missing data.audio"
            )

        try:
            audio = bytes.fromhex(audio_hex)
            log.info("minimax.tts.ok", bytes=len(audio))
            return audio
        except ValueError as exc:
            log.warning("minimax.tts.invalid_hex", error=str(exc))
            raise UpstreamFailureError(
                provider=_PROVIDER, message="data.audio is not valid hex"
            ) from exc
