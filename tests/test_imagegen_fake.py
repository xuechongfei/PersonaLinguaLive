from __future__ import annotations
import pytest
from app.adapters.imagegen.fake import FakeImageGenAdapter


@pytest.mark.asyncio
async def test_text_to_image_returns_png_bytes():
    adapter = FakeImageGenAdapter()
    result = await adapter.text_to_image("a cup")
    assert result.image_bytes.startswith(b"\x89PNG")
    assert result.mime == "image/png"


@pytest.mark.asyncio
async def test_image_to_image_returns_png_bytes():
    adapter = FakeImageGenAdapter()
    src = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16
    result = await adapter.image_to_image(src, "make it cartoon")
    assert result.image_bytes.startswith(b"\x89PNG")


@pytest.mark.asyncio
async def test_text_to_image_is_deterministic():
    adapter = FakeImageGenAdapter()
    a = await adapter.text_to_image("a cup")
    b = await adapter.text_to_image("a cup")
    assert a.image_bytes == b.image_bytes
