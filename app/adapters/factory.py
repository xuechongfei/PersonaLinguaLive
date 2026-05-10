"""Provider factory: pick vision adapter based on settings."""
from __future__ import annotations

from app.adapters.vision.base import VisionAdapter
from app.adapters.vision.fake import FakeVisionAdapter
from app.adapters.vision.openai_vision import OpenAIVisionAdapter
from app.config import Settings


def build_vision_adapter(settings: Settings) -> VisionAdapter:
    if settings.ai_vision_provider == "fake":
        return FakeVisionAdapter()
    if settings.ai_vision_provider == "openai":
        if settings.openai_api_key is None:
            # 应该已被 Settings.model_validator 拦下,但保险起见再校验
            raise RuntimeError("openai provider selected but PLL_OPENAI_API_KEY is missing")
        return OpenAIVisionAdapter(
            api_key=settings.openai_api_key.get_secret_value(),
            base_url=settings.openai_base_url,
            model=settings.openai_model_vision,
            timeout_s=settings.openai_request_timeout_s,
        )
    raise RuntimeError(f"unknown vision provider: {settings.ai_vision_provider}")
