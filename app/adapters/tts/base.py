"""TTSAdapter Protocol for text-to-speech synthesis."""
from __future__ import annotations

from typing import Protocol


class TTSAdapter(Protocol):
    """Provider-agnostic interface for text-to-speech."""

    async def synthesize(
        self,
        text: str,
        *,
        voice: str = "alloy",
    ) -> bytes:
        """Synthesize text to audio bytes (WAV/MP3 depending on provider)."""
        ...
