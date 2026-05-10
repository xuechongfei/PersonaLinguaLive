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
