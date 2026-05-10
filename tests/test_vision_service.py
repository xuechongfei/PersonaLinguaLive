"""Tests for app.services.vision_service.VisionService."""
from __future__ import annotations

import pytest

from app.schemas.vision import BBox, DetectedObject, VisionResult


class _StubAdapter:
    def __init__(self, result: VisionResult) -> None:
        self._result = result
        self.calls: list[bytes] = []

    async def analyze_image(self, image_bytes: bytes, *, intent: str = "safety_and_objects") -> VisionResult:
        self.calls.append(image_bytes)
        return self._result


def _obj(label: str, w: float, h: float, idx: int = 0) -> DetectedObject:
    return DetectedObject(
        id=f"o_{idx}",
        label=label,
        bbox=BBox(x=0.1, y=0.1, w=w, h=h),
        confidence=0.9,
        persona_seed=None,
    )


@pytest.mark.asyncio
async def test_passthrough_safe_result():
    from app.services.vision_service import VisionService

    adapter = _StubAdapter(
        VisionResult(
            is_safe=True,
            reject_reasons=[],
            scene_summary="kitchen",
            objects=[_obj("cupcake", 0.2, 0.2, idx=1)],
        )
    )
    svc = VisionService(adapter=adapter)
    out = await svc.analyze(b"\x00\x00")

    assert out.is_safe is True
    assert len(out.objects) == 1
    assert adapter.calls == [b"\x00\x00"]


@pytest.mark.asyncio
async def test_filters_small_objects_below_threshold():
    from app.services.vision_service import VisionService

    big = _obj("apple", 0.30, 0.20, idx=1)
    small = _obj("crumb", 0.05, 0.02, idx=2)  # area=0.001 < 0.015
    adapter = _StubAdapter(
        VisionResult(is_safe=True, scene_summary="", objects=[big, small])
    )
    out = await VisionService(adapter=adapter).analyze(b"x")

    labels = [o.label for o in out.objects]
    assert "apple" in labels
    assert "crumb" not in labels


@pytest.mark.asyncio
async def test_truncates_to_max_12_objects_keeping_largest():
    from app.services.vision_service import VisionService

    objects = [_obj(f"obj{i}", 0.10 + i * 0.01, 0.10, idx=i) for i in range(20)]
    adapter = _StubAdapter(
        VisionResult(is_safe=True, scene_summary="", objects=objects)
    )
    out = await VisionService(adapter=adapter).analyze(b"x")

    assert len(out.objects) == 12
    # 最大的 12 个被保留(area = w*h, h 固定 0.10,w 越大 area 越大)
    expected_labels = {f"obj{i}" for i in range(8, 20)}
    assert {o.label for o in out.objects} == expected_labels


@pytest.mark.asyncio
async def test_safety_guard_runs_before_returning():
    from app.services.vision_service import VisionService

    adapter = _StubAdapter(
        VisionResult(
            is_safe=False,
            reject_reasons=["face_detected"],
            scene_summary="cartoon character poster",
            objects=[_obj("poster", 0.3, 0.3, idx=1)],
        )
    )
    out = await VisionService(adapter=adapter).analyze(b"x")
    # SafetyGuard 把 cartoon 上的 face 误报清掉
    assert out.is_safe is True


@pytest.mark.asyncio
async def test_unsafe_result_clears_objects():
    from app.services.vision_service import VisionService

    adapter = _StubAdapter(
        VisionResult(
            is_safe=False,
            reject_reasons=["nsfw"],
            scene_summary="",
            objects=[_obj("anything", 0.3, 0.3, idx=1)],
        )
    )
    out = await VisionService(adapter=adapter).analyze(b"x")
    assert out.is_safe is False
    assert out.objects == []
