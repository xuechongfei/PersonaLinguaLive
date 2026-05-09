"""Application settings loaded from environment / .env."""
from __future__ import annotations

from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """所有运行期配置的唯一来源。环境变量前缀 PLL_。"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="PLL_",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "PersonaLinguaLive"
    app_version: str = "0.1.0"
    environment: Literal["development", "production", "test"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    cors_allow_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173"]
    )
    frontend_dist_dir: str = "frontend/dist"


def get_settings() -> Settings:
    """FastAPI Depends 用的工厂。后续可替换为 lru_cache。"""
    return Settings()
