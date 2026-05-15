"""Pydantic models for ambient events."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class AmbientEvent(BaseModel):
    npc_id: str
    event: Literal["glance", "gesture", "mumble"]
    target: str = ""
    text: str = ""
    duration_ms: int = Field(default=1000, ge=500)
