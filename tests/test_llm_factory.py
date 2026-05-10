"""Tests for build_llm_adapter factory."""
from __future__ import annotations

from app.adapters.factory import build_llm_adapter
from app.adapters.llm.fake import FakeLLMAdapter
from app.adapters.llm.openai_llm import OpenAILLMAdapter
from app.config import Settings


def test_fake_provider():
    settings = Settings(ai_llm_provider="fake")
    adapter = build_llm_adapter(settings)
    assert isinstance(adapter, FakeLLMAdapter)


def test_openai_provider(monkeypatch):
    monkeypatch.setenv("PLL_OPENAI_API_KEY", "sk-test")
    settings = Settings(ai_llm_provider="openai")
    adapter = build_llm_adapter(settings)
    assert isinstance(adapter, OpenAILLMAdapter)
    assert adapter._model == "gpt-4o-mini"
