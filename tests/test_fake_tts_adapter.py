"""Tests for FakeTTSAdapter."""
from __future__ import annotations

import wave
import io
import pytest


@pytest.mark.asyncio
async def test_synthesize_returns_wav_bytes():
    from app.adapters.tts.fake import FakeTTSAdapter

    adapter = FakeTTSAdapter()
    result = await adapter.synthesize("Hello")

    assert isinstance(result, bytes)
    assert len(result) > 44  # WAV header

    with wave.open(io.BytesIO(result), "rb") as wf:
        assert wf.getnchannels() == 1
        assert wf.getsampwidth() == 2
        assert wf.getframerate() == 8000


@pytest.mark.asyncio
async def test_longer_text_produces_longer_audio():
    from app.adapters.tts.fake import FakeTTSAdapter

    adapter = FakeTTSAdapter()
    short = await adapter.synthesize("Hi")
    long = await adapter.synthesize("Hello there, how are you today?")
    assert len(long) > len(short)


@pytest.mark.asyncio
async def test_records_last_text_and_voice():
    from app.adapters.tts.fake import FakeTTSAdapter

    adapter = FakeTTSAdapter()
    await adapter.synthesize("Test", voice="fable")
    assert adapter.last_text == "Test"
    assert adapter.last_voice == "fable"
