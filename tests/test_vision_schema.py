"""Tests for vision schema changes (Entity, kind, salience)."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.vision import BBox, Entity


class TestEntity:
    def test_entity_minimal(self):
        e = Entity(id="e1", kind="object", label="cup", bbox=BBox(x=0, y=0, w=0.5, h=0.5))
        assert e.salience == 0.0  # default
        assert e.seed is None

    def test_entity_character_kind(self):
        e = Entity(id="e2", kind="character", label="person",
                    bbox=BBox(x=0.1, y=0.1, w=0.3, h=0.8))
        assert e.kind == "character"

    def test_entity_invalid_kind_rejected(self):
        with pytest.raises(ValidationError):
            Entity(id="e3", kind="alien", label="x", bbox=BBox(x=0, y=0, w=0.5, h=0.5))

    def test_entity_salience_clamped(self):
        e = Entity(id="e4", kind="object", label="cup", bbox=BBox(x=0, y=0, w=0.5, h=0.5),
                    salience=1.5)
        assert e.salience == 1.0

    def test_entity_negative_salience_clamped(self):
        e = Entity(id="e5", kind="object", label="cup", bbox=BBox(x=0, y=0, w=0.5, h=0.5),
                    salience=-0.5)
        assert e.salience == 0.0
