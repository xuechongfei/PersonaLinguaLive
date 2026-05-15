"""Vision orchestration: adapter → SafetyGuard → post-filter."""
from __future__ import annotations

from app.adapters.vision.base import VisionAdapter
from app.schemas.vision import VisionResult
from app.services.safety_guard import SafetyGuard

_MAX_OBJECTS = 12
_MIN_OBJECT_AREA = 0.015  # 1.5% of total image area


class VisionService:
    def __init__(
        self,
        *,
        adapter: VisionAdapter,
        safety_guard: SafetyGuard | None = None,
    ) -> None:
        self._adapter = adapter
        self._safety = safety_guard or SafetyGuard()

    async def analyze(self, image_bytes: bytes) -> VisionResult:
        raw = await self._adapter.analyze_image(image_bytes)
        reviewed = self._safety.review(raw)

        if not reviewed.is_safe:
            return VisionResult(
                is_safe=False,
                reject_reasons=list(reviewed.reject_reasons),
                scene_summary=reviewed.scene_summary,
                raw_scene=reviewed.raw_scene,
                objects=[],
                entities=[],
            )

        # 过滤过小 + 截断到 _MAX_OBJECTS,保留面积最大的 12 个
        kept = [o for o in reviewed.objects if (o.bbox.w * o.bbox.h) >= _MIN_OBJECT_AREA]
        kept.sort(key=lambda o: o.bbox.w * o.bbox.h, reverse=True)
        kept = kept[:_MAX_OBJECTS]

        # Also filter entities by area for consistency
        kept_entities = [e for e in reviewed.entities if (e.bbox.w * e.bbox.h) >= _MIN_OBJECT_AREA]
        kept_entities.sort(key=lambda e: e.bbox.w * e.bbox.h, reverse=True)
        kept_entities = kept_entities[:_MAX_OBJECTS]

        return VisionResult(
            is_safe=True,
            reject_reasons=[],
            scene_summary=reviewed.scene_summary,
            raw_scene=reviewed.raw_scene,
            objects=kept,
            entities=kept_entities,
        )
