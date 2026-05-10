"""STTAdapter Protocol for speech-to-text transcription."""
from __future__ import annotations

from typing import Protocol


class STTAdapter(Protocol):
    """Provider-agnostic interface for speech-to-text."""

    async def transcribe(
        self,
        audio_bytes: bytes,
        *,
        language: str | None = None,
    ) -> str:
        """Transcribe audio bytes to text string."""
        ...
