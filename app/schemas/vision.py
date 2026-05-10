"""Pydantic models for /api/vision/analyze and adapter results."""
from __future__ import annotations

from pydantic import BaseModel, Field


class BBox(BaseModel):
    """Normalized bounding box (top-left origin, all values in [0, 1])."""

    x: float = Field(ge=0.0, le=1.0)
    y: float = Field(ge=0.0, le=1.0)
    w: float = Field(ge=0.0, le=1.0)
    h: float = Field(ge=0.0, le=1.0)


class DetectedObject(BaseModel):
    id: str
    label: str
    bbox: BBox
    confidence: float = Field(ge=0.0, le=1.0)
    persona_seed: str | None = None


class VisionResult(BaseModel):
    is_safe: bool
    reject_reasons: list[str] = Field(default_factory=list)
    scene_summary: str = ""
    objects: list[DetectedObject] = Field(default_factory=list)


class VisionAnalyzeResponse(BaseModel):
    request_id: str
    is_safe: bool
    reject_reasons: list[str] = Field(default_factory=list)
    scene_summary: str = ""
    objects: list[DetectedObject] = Field(default_factory=list)
