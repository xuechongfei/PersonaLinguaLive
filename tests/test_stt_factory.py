"""Tests for build_stt_adapter factory."""
from __future__ import annotations

from app.adapters.factory import build_stt_adapter
from app.adapters.stt.fake import FakeSTTAdapter
from app.adapters.stt.openai_stt import OpenAISTTAdapter
from app.config import Settings


def test_fake_provider():
    settings = Settings(ai_stt_provider="fake")
    adapter = build_stt_adapter(settings)
    assert isinstance(adapter, FakeSTTAdapter)


def test_openai_provider(monkeypatch):
    monkeypatch.setenv("PLL_OPENAI_API_KEY", "sk-test")
    settings = Settings(ai_stt_provider="openai")
    adapter = build_stt_adapter(settings)
    assert isinstance(adapter, OpenAISTTAdapter)
    assert adapter._model == "whisper-1"
