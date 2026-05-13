"""Tests for app.adapters.factory.build_vision_adapter."""
from __future__ import annotations


def test_factory_returns_fake_when_provider_is_fake(monkeypatch):
    monkeypatch.setenv("PLL_AI_VISION_PROVIDER", "fake")
    from app.adapters.factory import build_vision_adapter
    from app.adapters.vision.fake import FakeVisionAdapter
    from app.config import Settings

    adapter = build_vision_adapter(Settings())
    assert isinstance(adapter, FakeVisionAdapter)


def test_factory_returns_openai_adapter_when_configured(monkeypatch):
    monkeypatch.setenv("PLL_AI_VISION_PROVIDER", "openai")
    monkeypatch.setenv("PLL_OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("PLL_OPENAI_MODEL_VISION", "gpt-4o")

    from app.adapters.factory import build_vision_adapter
    from app.adapters.vision.openai_vision import OpenAIVisionAdapter
    from app.config import Settings

    adapter = build_vision_adapter(Settings())
    assert isinstance(adapter, OpenAIVisionAdapter)
    # 内部字段被正确传入
    assert adapter._api_key == "sk-test"
    assert adapter._model == "gpt-4o"


def test_qwen_provider(monkeypatch):
    monkeypatch.setenv("PLL_AI_VISION_PROVIDER", "qwen")
    monkeypatch.setenv("PLL_QWEN_API_KEY", "sk-qwen")
    from app.adapters.vision.qwen_vision import QwenVisionAdapter
    from app.adapters.factory import build_vision_adapter
    from app.config import Settings

    settings = Settings()
    adapter = build_vision_adapter(settings)
    assert isinstance(adapter, QwenVisionAdapter)
    assert adapter._model == "qwen-vl-max-latest"
    assert adapter._base_url == "https://dashscope.aliyuncs.com/compatible-mode/v1"
