"""Tests for app.config.Settings."""
from __future__ import annotations

import pytest


def test_settings_defaults():
    from app.config import Settings

    s = Settings()
    assert s.app_name == "PersonaLinguaLive"
    assert s.environment == "development"
    assert s.cors_allow_origins == ["http://localhost:5173"]
    assert s.frontend_dist_dir == "frontend/dist"
    assert s.log_level == "INFO"


def test_settings_env_override(monkeypatch):
    monkeypatch.setenv("PLL_ENVIRONMENT", "production")
    monkeypatch.setenv("PLL_LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("PLL_CORS_ALLOW_ORIGINS", '["https://pll.example.com"]')

    from app.config import Settings

    s = Settings()
    assert s.environment == "production"
    assert s.log_level == "DEBUG"
    assert s.cors_allow_origins == ["https://pll.example.com"]


def test_settings_invalid_environment(monkeypatch):
    monkeypatch.setenv("PLL_ENVIRONMENT", "staging")  # 不在枚举中

    from app.config import Settings

    with pytest.raises(ValueError):
        Settings()


def test_settings_ai_defaults():
    from app.config import Settings

    s = Settings()
    assert s.ai_vision_provider == "fake"
    assert s.openai_api_key is None
    assert s.openai_base_url == "https://api.openai.com/v1"
    assert s.openai_model_vision == "gpt-4o"
    assert s.openai_request_timeout_s == 30.0


def test_settings_upload_defaults():
    from app.config import Settings

    s = Settings()
    assert s.upload_max_bytes == 10 * 1024 * 1024
    assert s.upload_allowed_mime == ["image/jpeg", "image/png", "image/webp"]


def test_settings_rate_limit_defaults():
    from app.config import Settings

    s = Settings()
    assert s.rate_limit_vision_per_min == 6


def test_settings_openai_provider_requires_api_key(monkeypatch):
    monkeypatch.setenv("PLL_AI_VISION_PROVIDER", "openai")
    monkeypatch.delenv("PLL_OPENAI_API_KEY", raising=False)

    from app.config import Settings

    with pytest.raises(ValueError, match="PLL_OPENAI_API_KEY"):
        Settings()


def test_settings_openai_provider_accepts_api_key(monkeypatch):
    monkeypatch.setenv("PLL_AI_VISION_PROVIDER", "openai")
    monkeypatch.setenv("PLL_OPENAI_API_KEY", "sk-test-123")

    from app.config import Settings

    s = Settings()
    assert s.ai_vision_provider == "openai"
    assert s.openai_api_key.get_secret_value() == "sk-test-123"


def test_deepseek_provider_requires_deepseek_key(monkeypatch):
    monkeypatch.setenv("PLL_AI_LLM_PROVIDER", "deepseek")
    from app.config import Settings
    with pytest.raises(ValueError, match="PLL_DEEPSEEK_API_KEY"):
        Settings()


def test_deepseek_provider_loads_with_key(monkeypatch):
    monkeypatch.setenv("PLL_AI_LLM_PROVIDER", "deepseek")
    monkeypatch.setenv("PLL_DEEPSEEK_API_KEY", "sk-test")
    from app.config import Settings
    settings = Settings()
    assert settings.ai_llm_provider == "deepseek"
    assert settings.deepseek_api_key.get_secret_value() == "sk-test"
    assert settings.deepseek_base_url == "https://api.deepseek.com/v1"
    assert settings.deepseek_model_llm == "deepseek-v4-flash"


def test_qwen_provider_requires_qwen_key(monkeypatch):
    monkeypatch.setenv("PLL_AI_VISION_PROVIDER", "qwen")
    from app.config import Settings
    with pytest.raises(ValueError, match="PLL_QWEN_API_KEY"):
        Settings()


def test_qwen_provider_loads_with_key(monkeypatch):
    monkeypatch.setenv("PLL_AI_VISION_PROVIDER", "qwen")
    monkeypatch.setenv("PLL_QWEN_API_KEY", "sk-qwen")
    from app.config import Settings
    settings = Settings()
    assert settings.ai_vision_provider == "qwen"
    assert settings.qwen_api_key.get_secret_value() == "sk-qwen"
    assert settings.qwen_base_url == "https://dashscope.aliyuncs.com/compatible-mode/v1"
    assert settings.qwen_model_vision == "qwen-vl-max-latest"


def test_minimax_provider_requires_key_and_group_id(monkeypatch):
    monkeypatch.setenv("PLL_AI_TTS_PROVIDER", "minimax")
    from app.config import Settings
    with pytest.raises(ValueError, match="PLL_MINIMAX_API_KEY"):
        Settings()
    monkeypatch.setenv("PLL_MINIMAX_API_KEY", "sk-mm")
    with pytest.raises(ValueError, match="PLL_MINIMAX_GROUP_ID"):
        Settings()


def test_minimax_provider_loads_with_key_and_group(monkeypatch):
    monkeypatch.setenv("PLL_AI_TTS_PROVIDER", "minimax")
    monkeypatch.setenv("PLL_MINIMAX_API_KEY", "sk-mm")
    monkeypatch.setenv("PLL_MINIMAX_GROUP_ID", "grp123")
    from app.config import Settings
    settings = Settings()
    assert settings.ai_tts_provider == "minimax"
    assert settings.minimax_api_key.get_secret_value() == "sk-mm"
    assert settings.minimax_group_id == "grp123"
    assert settings.minimax_base_url == "https://api.minimaxi.chat/v1"
    assert settings.minimax_model_tts == "speech-02-hd"
    assert settings.minimax_default_voice == "English_expressive_narrator"
