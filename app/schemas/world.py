"""Pydantic models for SceneBible, WorldAssets, and SSE event payloads."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


# ---- Voice ----

class VoiceTraits(BaseModel):
    gender: Literal["female", "male"] = "female"
    age: Literal["child", "adult", "elder"] = "adult"
    tone: Literal["warm", "sweet", "confident", "neutral", "playful", "gruff"] = "warm"


# ---- World / Environment ----

class WorldSpec(BaseModel):
    place: str
    time_of_day: str
    weather: str
    mood: str
    ambient_sounds: list[str] = Field(default_factory=list)
    bgm_mood: str = ""
    art_style_prompt: str = ""


# ---- NPC ----

class NPCSpec(BaseModel):
    entity_id: str
    kind: Literal["object", "character"]
    persona_name: str
    role_in_scene: str
    relationship_to_user: str = ""
    personality: str = ""
    voice_traits: VoiceTraits = Field(default_factory=VoiceTraits)
    vocab_focus: list[str] = Field(default_factory=list)
    ambient_actions: list[str] = Field(default_factory=list)


class CrossRelationship(BaseModel):
    from_entity: str
    to_entity: str
    note: str


# ---- SceneBible (the central generation artifact) ----

class SceneBible(BaseModel):
    world: WorldSpec
    npcs: list[NPCSpec]
    cross_relationships: list[CrossRelationship] = Field(default_factory=list)


# ---- Asset related ----

class SpriteSet(BaseModel):
    default: str  # base64
    blink: str = ""
    mouth_a: str = ""
    mouth_b: str = ""
    mouth_c: str = ""


class NPCSprites(BaseModel):
    entity_id: str
    sprites: SpriteSet
    position_x: float = Field(default=0.5, ge=0.0, le=1.0)
    position_y: float = Field(default=0.5, ge=0.0, le=1.0)


class WorldAssets(BaseModel):
    background_base64: str = ""
    sprites: list[NPCSprites] = Field(default_factory=list)


# ---- SSE event types ----

class WorldAssetStatus(BaseModel):
    world_id: str
    state: Literal["pending", "bible_ready", "background_ready", "sprite_ready", "world_ready", "error"] = "pending"
    event_data: dict = Field(default_factory=dict)
