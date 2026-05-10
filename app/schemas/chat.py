"""Pydantic schemas for chat and summary."""
from __future__ import annotations

from pydantic import BaseModel, Field


class ChatSegment(BaseModel):
    speak: str = ""
    learning: str = ""
    followup: str = ""


class ChatTurn(BaseModel):
    user_message: str
    assistant_response: ChatSegment = Field(default_factory=ChatSegment)
    timestamp: float = 0.0


class ChatSummaryRequest(BaseModel):
    session_id: str
    user_level: str = "beginner"


class ChatSummaryResponse(BaseModel):
    new_words: list[str] = Field(default_factory=list)
    grammar_points: list[str] = Field(default_factory=list)
    fluency_score: int = Field(default=5, ge=1, le=10)
    strengths: list[str] = Field(default_factory=list)
    areas_to_improve: list[str] = Field(default_factory=list)
