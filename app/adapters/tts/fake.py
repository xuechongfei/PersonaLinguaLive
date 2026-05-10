"""FakeTTSAdapter: returns minimal WAV bytes for tests + offline."""
from __future__ import annotations

import io
import struct
import wave


class FakeTTSAdapter:
    def __init__(self) -> None:
        self.last_text: str | None = None
        self.last_voice: str | None = None

    async def synthesize(
        self,
        text: str,
        *,
        voice: str = "alloy",
    ) -> bytes:
        self.last_text = text
        self.last_voice = voice

        duration_s = max(0.5, len(text) * 0.05)
        sample_rate = 8000
        num_samples = int(sample_rate * duration_s)

        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            for i in range(num_samples):
                value = int(16000 * 0.3 * ((i % 100) / 100))
                wf.writeframes(struct.pack("<h", value))
        return buf.getvalue()
