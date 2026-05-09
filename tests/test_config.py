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
