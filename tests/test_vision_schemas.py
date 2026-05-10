"""Tests for app.schemas.vision."""
from __future__ import annotations

import pytest
from pydantic import ValidationError


def test_bbox_accepts_normalized_floats():
    from app.schemas.vision import BBox

    b = BBox(x=0.1, y=0.2, w=0.3, h=0.4)
    assert b.x == 0.1
    assert b.h == 0.4


def test_bbox_rejects_out_of_range():
    from app.schemas.vision import BBox

    with pytest.raises(ValidationError):
        BBox(x=-0.1, y=0, w=0.5, h=0.5)
    with pytest.raises(ValidationError):
        BBox(x=0, y=0, w=1.5, h=0.5)


def test_detected_object_round_trip():
    from app.schemas.vision import BBox, DetectedObject

    obj = DetectedObject(
        id="o_1",
        label="cupcake",
        bbox=BBox(x=0.1, y=0.1, w=0.2, h=0.2),
        confidence=0.9,
        persona_seed="sweet baker",
    )
    data = obj.model_dump()
    assert data["id"] == "o_1"
    assert data["confidence"] == 0.9
    assert data["bbox"] == {"x": 0.1, "y": 0.1, "w": 0.2, "h": 0.2}


def test_detected_object_rejects_confidence_out_of_range():
    from app.schemas.vision import BBox, DetectedObject

    with pytest.raises(ValidationError):
        DetectedObject(
            id="o_1",
            label="x",
            bbox=BBox(x=0, y=0, w=0.1, h=0.1),
            confidence=1.2,
        )


def test_vision_result_defaults():
    from app.schemas.vision import VisionResult

    r = VisionResult(is_safe=True)
    assert r.is_safe is True
    assert r.reject_reasons == []
    assert r.scene_summary == ""
    assert r.objects == []


def test_vision_analyze_response_shape():
    from app.schemas.vision import VisionAnalyzeResponse

    payload = VisionAnalyzeResponse(
        request_id="req_abc",
        is_safe=True,
        reject_reasons=[],
        scene_summary="kitchen",
        objects=[],
    )
    dumped = payload.model_dump()
    assert dumped["request_id"] == "req_abc"
    assert dumped["scene_summary"] == "kitchen"
