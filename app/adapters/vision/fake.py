"""FakeVisionAdapter: deterministic stub for tests + offline development."""
from __future__ import annotations

import structlog

from app.adapters.vision.base import VisionIntent
from app.schemas.vision import BBox, DetectedObject, Entity, VisionResult

log = structlog.get_logger("pll.adapter.fake_vision")

_TRIGGERS: dict[bytes, str] = {
    b"PLL_FAKE_NSFW": "nsfw",
    b"PLL_FAKE_TEXT": "dominant_text",
    b"PLL_FAKE_UNCLEAR": "unclear_image",
    b"PLL_FAKE_VIOLENCE": "violence",
    b"PLL_FAKE_WEAPON": "weapons",
}

_SCENE_SUMMARY = "A bright kitchen counter with baking ingredients arranged neatly."

_DEFAULT_OBJECTS = [
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
]

_DEFAULT_ENTITIES = [
    Entity(
        id="e1",
        kind="object",
        label="cupcake",
        bbox=BBox(x=0.42, y=0.55, w=0.18, h=0.22),
        confidence=0.92,
        salience=0.9,
        seed="sweet baker who loves sharing recipes",
    ),
    Entity(
        id="e2",
        kind="object",
        label="saucepan",
        bbox=BBox(x=0.10, y=0.30, w=0.20, h=0.25),
        confidence=0.88,
        salience=0.7,
        seed="gruff old chef with decades of stories",
    ),
    Entity(
        id="e3",
        kind="object",
        label="apple",
        bbox=BBox(x=0.68, y=0.40, w=0.12, h=0.16),
        confidence=0.81,
        salience=0.5,
        seed="cheerful and chatty about orchards",
    ),
]

_DEFAULT_SAFE = VisionResult(
    is_safe=True,
    reject_reasons=[],
    scene_summary=_SCENE_SUMMARY,
    raw_scene=_SCENE_SUMMARY,
    objects=_DEFAULT_OBJECTS,
    entities=_DEFAULT_ENTITIES,
)


class FakeVisionAdapter:
    async def analyze_image(
        self,
        image_bytes: bytes,
        *,
        intent: VisionIntent = "safety_and_objects",
    ) -> VisionResult:
        log.info("fake.vision.call", image_bytes=len(image_bytes))
        head = image_bytes[:32]
        for marker, reason in _TRIGGERS.items():
            if marker in head:
                log.info("fake.vision.unsafe", reason=reason)
                return VisionResult(
                    is_safe=False,
                    reject_reasons=[reason],
                    scene_summary="",
                    raw_scene="",
                    objects=[],
                    entities=[],
                )
        result = _DEFAULT_SAFE.model_copy(deep=True)
        log.info("fake.vision.ok", entities=len(result.entities))
        return result
