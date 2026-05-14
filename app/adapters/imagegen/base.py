"""ImageGenAdapter protocol: text-to-image and image-to-image."""
from __future__ import annotations

from typing import Protocol


class ImageGenResult:
    __slots__ = ("image_bytes", "mime")

    def __init__(self, image_bytes: bytes, mime: str = "image/png") -> None:
        self.image_bytes = image_bytes
        self.mime = mime


class ImageGenAdapter(Protocol):
    async def text_to_image(
        self,
        prompt: str,
        *,
        size: str = "1024x1024",
        reference_image: bytes | None = None,
    ) -> ImageGenResult: ...

    async def image_to_image(
        self,
        image_bytes: bytes,
        prompt: str,
        *,
        size: str = "1024x1024",
        strength: float = 0.7,
    ) -> ImageGenResult: ...
