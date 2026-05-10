"""FakeVisionAdapter: deterministic stub for tests + offline development."""
from __future__ import annotations

from app.adapters.vision.base import VisionIntent
from app.schemas.vision import BBox, DetectedObject, VisionResult

_TRIGGERS: dict[bytes, str] = {
    b"PLL_FAKE_FACE": "face_detected",
    b"PLL_FAKE_NSFW": "nsfw",
    b"PLL_FAKE_TEXT": "dominant_text",
    b"PLL_FAKE_UNCLEAR": "unclear_image",
    b"PLL_FAKE_VIOLENCE": "violence",
    b"PLL_FAKE_WEAPON": "weapons",
}

_DEFAULT_SAFE = VisionResult(
    is_safe=True,
    reject_reasons=[],
    scene_summary="A bright kitchen counter with baking ingredients arranged neatly.",
    objects=[
        DetectedObject(
            id="o_1",
            label="cupcake",
            bbox=BBox(x=0.42, y=0.55, w=0.18, h=0.22),
            confidence=0.92,
            persona_seed="sweet baker who loves sharing recipes",
        ),
        DetectedObject(
            id="o_2",
            label="saucepan",
            bbox=BBox(x=0.10, y=0.30, w=0.20, h=0.25),
            confidence=0.88,
            persona_seed="gruff old chef with decades of stories",
        ),
        DetectedObject(
            id="o_3",
            label="apple",
            bbox=BBox(x=0.68, y=0.40, w=0.12, h=0.16),
            confidence=0.81,
            persona_seed="cheerful and chatty about orchards",
        ),
    ],
)


class FakeVisionAdapter:
    async def analyze_image(
        self,
        image_bytes: bytes,
        *,
        intent: VisionIntent = "safety_and_objects",
    ) -> VisionResult:
        head = image_bytes[:32]
        for marker, reason in _TRIGGERS.items():
            if marker in head:
                return VisionResult(
                    is_safe=False,
                    reject_reasons=[reason],
                    scene_summary="",
                    objects=[],
                )
        return _DEFAULT_SAFE.model_copy(deep=True)
