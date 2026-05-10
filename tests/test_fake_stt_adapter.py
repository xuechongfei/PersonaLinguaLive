"""Tests for FakeSTTAdapter."""
from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_transcribe_default():
    from app.adapters.stt.fake import FakeSTTAdapter

    adapter = FakeSTTAdapter()
    result = await adapter.transcribe(b"some random audio")
    assert result == "I am learning English."


@pytest.mark.asyncio
async def test_transcribe_trigger_hello():
    from app.adapters.stt.fake import FakeSTTAdapter

    adapter = FakeSTTAdapter()
    result = await adapter.transcribe(b"PLL_FAKE_HELLO world")
    assert result == "Hello, how are you?"


@pytest.mark.asyncio
async def test_transcribe_trigger_teach():
    from app.adapters.stt.fake import FakeSTTAdapter

    adapter = FakeSTTAdapter()
    result = await adapter.transcribe(b"PLL_FAKE_TEACH me")
    assert result == "I want to learn English."


@pytest.mark.asyncio
async def test_records_last_audio_and_language():
    from app.adapters.stt.fake import FakeSTTAdapter

    adapter = FakeSTTAdapter()
    audio = b"PLL_FAKE_HELLO test"
    await adapter.transcribe(audio, language="en")
    assert adapter.last_audio == audio
    assert adapter.last_language == "en"
