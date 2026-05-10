"""Application settings loaded from environment / .env."""
from __future__ import annotations

from typing import Literal

from pydantic import Field, SecretStr, model_validator
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

    # === AI 适配层 ===
    ai_vision_provider: Literal["fake", "openai"] = "fake"
    openai_api_key: SecretStr | None = None
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model_vision: str = "gpt-4o"
    openai_request_timeout_s: float = 30.0

    # === 上传约束 ===
    upload_max_bytes: int = 10 * 1024 * 1024  # 10 MiB
    upload_allowed_mime: list[str] = Field(
        default_factory=lambda: ["image/jpeg", "image/png", "image/webp"]
    )

    # === 限流(单实例内存桶,IP 维度)===
    rate_limit_vision_per_min: int = 6

    @model_validator(mode="after")
    def _validate_provider_credentials(self) -> "Settings":
        if self.ai_vision_provider == "openai" and self.openai_api_key is None:
            raise ValueError(
                "PLL_OPENAI_API_KEY is required when AI_VISION_PROVIDER=openai"
            )
        return self


def get_settings() -> Settings:
    """FastAPI Depends 用的工厂。"""
    return Settings()
