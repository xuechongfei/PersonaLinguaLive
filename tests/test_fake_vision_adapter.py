"""Tests for FakeVisionAdapter."""
from __future__ import annotations

import pytest

from tests.fixtures.images import (
    fake_face_bytes,
    fake_nsfw_bytes,
    fake_text_bytes,
    fake_unclear_bytes,
    safe_png_bytes,
)


@pytest.mark.asyncio
async def test_fake_returns_default_safe_objects_for_real_png():
    from app.adapters.vision.fake import FakeVisionAdapter

    result = await FakeVisionAdapter().analyze_image(safe_png_bytes())

    assert result.is_safe is True
    assert result.reject_reasons == []
    assert result.scene_summary
    assert len(result.objects) >= 3
    for obj in result.objects:
        assert obj.label
        assert 0.0 <= obj.bbox.x <= 1.0
        assert 0.0 < obj.bbox.w <= 1.0


@pytest.mark.asyncio
async def test_fake_face_returns_safe_in_v3():
    from app.adapters.vision.fake import FakeVisionAdapter

    result = await FakeVisionAdapter().analyze_image(fake_face_bytes())
    assert result.is_safe is True
    assert "face_detected" not in result.reject_reasons


@pytest.mark.asyncio
async def test_fake_nsfw_trigger_returns_unsafe():
    from app.adapters.vision.fake import FakeVisionAdapter

    result = await FakeVisionAdapter().analyze_image(fake_nsfw_bytes())
    assert result.is_safe is False
    assert "nsfw" in result.reject_reasons


@pytest.mark.asyncio
async def test_fake_text_trigger_returns_unsafe():
    from app.adapters.vision.fake import FakeVisionAdapter

    result = await FakeVisionAdapter().analyze_image(fake_text_bytes())
    assert result.is_safe is False
    assert "dominant_text" in result.reject_reasons


@pytest.mark.asyncio
async def test_fake_unclear_trigger_returns_unsafe():
    from app.adapters.vision.fake import FakeVisionAdapter

    result = await FakeVisionAdapter().analyze_image(fake_unclear_bytes())
    assert result.is_safe is False
    assert "unclear_image" in result.reject_reasons


@pytest.mark.asyncio
async def test_fake_object_ids_are_unique():
    from app.adapters.vision.fake import FakeVisionAdapter

    result = await FakeVisionAdapter().analyze_image(safe_png_bytes())
    ids = [o.id for o in result.objects]
    assert len(ids) == len(set(ids))
