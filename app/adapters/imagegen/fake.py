"""Deterministic fake image generator. Returns a 1x1 PNG keyed by prompt hash."""
from __future__ import annotations

import hashlib
import struct
import zlib

import structlog

from app.adapters.imagegen.base import ImageGenAdapter, ImageGenResult

log = structlog.get_logger("pll.adapter.fake_imagegen")


def _png_1x1(rgba: tuple[int, int, int, int]) -> bytes:
    sig = b"\x89PNG\r\n\x1a\n"

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0)
    raw = bytes([0]) + bytes(rgba)
    idat = zlib.compress(raw)
    return sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")


class FakeImageGenAdapter(ImageGenAdapter):
    async def text_to_image(self, prompt, *, size="1024x1024", reference_image=None):
        log.info("fake.imagegen.text_to_image.call", size=size)
        d = hashlib.sha256(prompt.encode("utf-8")).digest()
        return ImageGenResult(_png_1x1((d[0], d[1], d[2], 255)), "image/png")

    async def image_to_image(self, image_bytes, prompt, *, size="1024x1024", strength=0.7):
        log.info("fake.imagegen.image_to_image.call", size=size, src_bytes=len(image_bytes))
        d = hashlib.sha256(prompt.encode("utf-8") + image_bytes[:64]).digest()
        return ImageGenResult(_png_1x1((d[0], d[1], d[2], 255)), "image/png")
