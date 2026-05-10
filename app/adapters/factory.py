"""Provider factory: pick vision adapter based on settings."""
from __future__ import annotations

from app.adapters.vision.base import VisionAdapter
from app.adapters.vision.fake import FakeVisionAdapter
from app.config import Settings


def build_vision_adapter(settings: Settings) -> VisionAdapter:
    if settings.ai_vision_provider == "fake":
        return FakeVisionAdapter()
    # OpenAI 分支留 Task 11
    raise NotImplementedError(f"vision provider not yet wired: {settings.ai_vision_provider}")
