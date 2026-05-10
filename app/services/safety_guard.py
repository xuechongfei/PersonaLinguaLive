"""Rule-based second pass on top of VisionAdapter output."""
from __future__ import annotations

from app.schemas.vision import VisionResult

_TOY_KEYWORDS = ("toy", "plush", "teddy", "doll", "figurine", "cartoon", "animated", "poster")
_TEXT_LABELS = {"text", "writing", "document", "handwriting", "sign"}


class SafetyGuard:
    """Apply additional content-safety rules on top of an adapter result."""

    def review(self, result: VisionResult) -> VisionResult:
        reasons = list(result.reject_reasons)
        is_safe = result.is_safe

        # Rule 1: face detection on toys/cartoons is a likely false positive.
        summary_lower = result.scene_summary.lower()
        if "face_detected" in reasons and any(kw in summary_lower for kw in _TOY_KEYWORDS):
            reasons = [r for r in reasons if r != "face_detected"]
            if not reasons:
                is_safe = True

        # Rule 2: text-dominant scenes (>=40% area) get rejected even if model said safe.
        text_area = sum(o.bbox.w * o.bbox.h for o in result.objects if o.label.lower() in _TEXT_LABELS)
        if text_area >= 0.40 and "dominant_text" not in reasons:
            reasons.append("dominant_text")
            is_safe = False

        return VisionResult(
            is_safe=is_safe,
            reject_reasons=reasons,
            scene_summary=result.scene_summary,
            objects=result.objects,
        )
