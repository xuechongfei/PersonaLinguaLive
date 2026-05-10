"""Tests for app.services.safety_guard.SafetyGuard."""
from __future__ import annotations

from app.schemas.vision import BBox, DetectedObject, VisionResult


def _safe_result_with(objects: list[DetectedObject], summary: str = "") -> VisionResult:
    return VisionResult(is_safe=True, reject_reasons=[], scene_summary=summary, objects=objects)


def _obj(label: str, *, x=0.1, y=0.1, w=0.1, h=0.1) -> DetectedObject:
    return DetectedObject(
        id=f"o_{label}",
        label=label,
        bbox=BBox(x=x, y=y, w=w, h=h),
        confidence=0.9,
        persona_seed=None,
    )


def test_passthrough_for_clean_safe_result():
    from app.services.safety_guard import SafetyGuard

    inp = _safe_result_with([_obj("cupcake")])
    out = SafetyGuard().review(inp)
    assert out.is_safe is True
    assert out.reject_reasons == []


def test_face_detected_is_zero_tolerance():
    from app.services.safety_guard import SafetyGuard

    inp = VisionResult(
        is_safe=False,
        reject_reasons=["face_detected"],
        scene_summary="A family photo at the beach.",
        objects=[],
    )
    out = SafetyGuard().review(inp)
    assert out.is_safe is False
    assert "face_detected" in out.reject_reasons


def test_face_on_toy_is_overridden_to_safe():
    from app.services.safety_guard import SafetyGuard

    inp = VisionResult(
        is_safe=False,
        reject_reasons=["face_detected"],
        scene_summary="A plush teddy bear toy on a kid's bed.",
        objects=[_obj("teddy_bear")],
    )
    out = SafetyGuard().review(inp)
    assert out.is_safe is True
    assert out.reject_reasons == []
    assert out.objects == inp.objects


def test_face_on_cartoon_is_overridden_to_safe():
    from app.services.safety_guard import SafetyGuard

    inp = VisionResult(
        is_safe=False,
        reject_reasons=["face_detected"],
        scene_summary="A cartoon poster of an animated character.",
        objects=[_obj("poster")],
    )
    out = SafetyGuard().review(inp)
    assert out.is_safe is True


def test_dominant_text_objects_rejected_even_if_model_says_safe():
    from app.services.safety_guard import SafetyGuard

    objects = [
        _obj("text", w=0.7, h=0.6),
        _obj("apple", w=0.05, h=0.05),
    ]
    inp = _safe_result_with(objects)
    out = SafetyGuard().review(inp)
    assert out.is_safe is False
    assert "dominant_text" in out.reject_reasons


def test_partial_text_within_scene_is_kept_safe():
    from app.services.safety_guard import SafetyGuard

    objects = [
        _obj("text", w=0.05, h=0.05),
        _obj("apple", w=0.4, h=0.4),
    ]
    inp = _safe_result_with(objects)
    out = SafetyGuard().review(inp)
    assert out.is_safe is True


def test_other_unsafe_reasons_passthrough():
    from app.services.safety_guard import SafetyGuard

    inp = VisionResult(
        is_safe=False,
        reject_reasons=["nsfw"],
        scene_summary="",
        objects=[],
    )
    out = SafetyGuard().review(inp)
    assert out.is_safe is False
    assert "nsfw" in out.reject_reasons
