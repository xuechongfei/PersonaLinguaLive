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
    ai_vision_provider: Literal["fake", "openai", "qwen"] = "fake"
    ai_llm_provider: Literal["fake", "openai", "deepseek"] = "fake"
    ai_tts_provider: Literal["fake", "openai", "minimax"] = "fake"
    ai_stt_provider: Literal["fake", "openai"] = "fake"

    # OpenAI
    openai_api_key: SecretStr | None = None
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model_vision: str = "gpt-4o"
    openai_model_llm: str = "gpt-4o-mini"
    openai_model_tts: str = "tts-1-hd"
    openai_model_stt: str = "whisper-1"
    openai_tts_voice: str = "alloy"
    openai_request_timeout_s: float = 30.0

    # DeepSeek (LLM, OpenAI-compatible)
    deepseek_api_key: SecretStr | None = None
    deepseek_base_url: str = "https://api.deepseek.com/v1"
    deepseek_model_llm: str = "deepseek-v4-flash"
    deepseek_request_timeout_s: float = 30.0

    # Qwen-VL (Vision, DashScope compatible-mode)
    qwen_api_key: SecretStr | None = None
    qwen_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    qwen_model_vision: str = "qwen-vl-max-latest"
    qwen_request_timeout_s: float = 30.0

    # MiniMax (TTS)
    minimax_api_key: SecretStr | None = None
    minimax_group_id: str | None = None
    minimax_base_url: str = "https://api.minimaxi.chat/v1"
    minimax_model_tts: str = "speech-02-hd"
    minimax_default_voice: str = "English_expressive_narrator"
    minimax_request_timeout_s: float = 30.0

    # === 上传约束 ===
    upload_max_bytes: int = 10 * 1024 * 1024  # 10 MiB
    upload_allowed_mime: list[str] = Field(
        default_factory=lambda: ["image/jpeg", "image/png", "image/webp"]
    )

    # === 限流(单实例内存桶,IP 维度)===
    rate_limit_vision_per_min: int = 6
    rate_limit_persona_per_min: int = 10
    rate_limit_chat_messages_per_min: int = 30

    @model_validator(mode="after")
    def _validate_provider_credentials(self) -> Settings:
        uses_openai = "openai" in (
            self.ai_vision_provider,
            self.ai_llm_provider,
            self.ai_tts_provider,
            self.ai_stt_provider,
        )
        if uses_openai and self.openai_api_key is None:
            raise ValueError(
                "PLL_OPENAI_API_KEY is required when any AI provider is set to 'openai'"
            )
        if self.ai_llm_provider == "deepseek" and self.deepseek_api_key is None:
            raise ValueError(
                "PLL_DEEPSEEK_API_KEY is required when LLM provider is 'deepseek'"
            )
        if self.ai_vision_provider == "qwen" and self.qwen_api_key is None:
            raise ValueError(
                "PLL_QWEN_API_KEY is required when vision provider is 'qwen'"
            )
        if self.ai_tts_provider == "minimax":
            if self.minimax_api_key is None:
                raise ValueError(
                    "PLL_MINIMAX_API_KEY is required when TTS provider is 'minimax'"
                )
            if not self.minimax_group_id:
                raise ValueError(
                    "PLL_MINIMAX_GROUP_ID is required when TTS provider is 'minimax'"
                )
        return self


def get_settings() -> Settings:
    """FastAPI Depends 用的工厂。"""
    return Settings()
