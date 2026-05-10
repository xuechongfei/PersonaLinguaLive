"""Pydantic schemas for persona generation."""
from __future__ import annotations

from pydantic import BaseModel, Field


class PersonaGenerateRequest(BaseModel):
    label: str = Field(..., min_length=1, description="Object label (e.g. 'cupcake')")
    persona_seed: str = Field(default="", description="Optional seed hint from vision analysis")
    scene_summary: str = Field(default="", description="Scene context from vision analysis")
    user_level: str = Field(default="beginner", description="beginner | intermediate | advanced")


class PersonaGenerateResponse(BaseModel):
    persona_id: str
    persona_name: str
    description: str
    system_prompt: str
    vocab_focus: list[str] = Field(default_factory=list)
