"""Helpers to build test image byte strings."""
from __future__ import annotations

# 真实 1x1 px PNG(透明)。FakeVisionAdapter 会落入 'safe' 分支。
_PNG_1X1 = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xfa\xcf"
    b"\x00\x00\x00\x02\x00\x01\xe2!\xbc3\x00\x00\x00\x00IEND\xaeB`\x82"
)


def safe_png_bytes() -> bytes:
    return _PNG_1X1


def fake_face_bytes() -> bytes:
    return b"PLL_FAKE_FACE\x00" + b"\x00" * 64


def fake_nsfw_bytes() -> bytes:
    return b"PLL_FAKE_NSFW\x00" + b"\x00" * 64


def fake_text_bytes() -> bytes:
    return b"PLL_FAKE_TEXT\x00" + b"\x00" * 64


def fake_unclear_bytes() -> bytes:
    return b"PLL_FAKE_UNCLEAR\x00" + b"\x00" * 64
