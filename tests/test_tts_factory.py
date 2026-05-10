"""Tests for build_tts_adapter factory."""
from __future__ import annotations

from app.adapters.factory import build_tts_adapter
from app.adapters.tts.fake import FakeTTSAdapter
from app.adapters.tts.openai_tts import OpenAITTSAdapter
from app.config import Settings


def test_fake_provider():
    settings = Settings(ai_tts_provider="fake")
    adapter = build_tts_adapter(settings)
    assert isinstance(adapter, FakeTTSAdapter)


def test_openai_provider(monkeypatch):
    monkeypatch.setenv("PLL_OPENAI_API_KEY", "sk-test")
    settings = Settings(ai_tts_provider="openai")
    adapter = build_tts_adapter(settings)
    assert isinstance(adapter, OpenAITTSAdapter)
    assert adapter._model == "tts-1-hd"
