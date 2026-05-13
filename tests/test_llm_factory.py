"""Tests for build_llm_adapter factory."""
from __future__ import annotations

import pytest

from app.adapters.factory import build_llm_adapter
from app.adapters.llm.fake import FakeLLMAdapter
from app.adapters.llm.openai_llm import OpenAILLMAdapter
from app.adapters.llm.deepseek_llm import DeepSeekLLMAdapter
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


def test_deepseek_provider(monkeypatch):
    monkeypatch.setenv("PLL_AI_LLM_PROVIDER", "deepseek")
    monkeypatch.setenv("PLL_DEEPSEEK_API_KEY", "sk-ds")

    settings = Settings()
    adapter = build_llm_adapter(settings)
    assert isinstance(adapter, DeepSeekLLMAdapter)
    assert adapter._model == "deepseek-v4-flash"
    assert adapter._base_url == "https://api.deepseek.com/v1"


def test_deepseek_provider_without_key_raises(monkeypatch):
    monkeypatch.setenv("PLL_AI_LLM_PROVIDER", "deepseek")
    with pytest.raises(ValueError, match="PLL_DEEPSEEK_API_KEY"):
        Settings()
