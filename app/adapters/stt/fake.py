"""FakeSTTAdapter: returns deterministic text for tests + offline."""
from __future__ import annotations


class FakeSTTAdapter:
    def __init__(self) -> None:
        self.last_audio: bytes | None = None
        self.last_language: str | None = None

    async def transcribe(
        self,
        audio_bytes: bytes,
        *,
        language: str | None = None,
    ) -> str:
        self.last_audio = audio_bytes
        self.last_language = language

        if b"PLL_FAKE_HELLO" in audio_bytes[:64]:
            return "Hello, how are you?"
        if b"PLL_FAKE_TEACH" in audio_bytes[:64]:
            return "I want to learn English."
        return "I am learning English."
