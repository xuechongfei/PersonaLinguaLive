"""VisionAdapter Protocol and shared types."""
from __future__ import annotations

from typing import Literal, Protocol

from app.schemas.vision import VisionResult

VisionIntent = Literal["safety_and_objects"]


class VisionAdapter(Protocol):
    """Provider-agnostic interface for image safety + object detection."""

    async def analyze_image(
        self,
        image_bytes: bytes,
        *,
        intent: VisionIntent = "safety_and_objects",
    ) -> VisionResult: ...
