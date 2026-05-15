from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.ambient import AmbientEvent


def test_ambient_glance_event():
    e = AmbientEvent(npc_id="e3", event="glance", target="e1", duration_ms=1000)
    assert e.event == "glance"
    assert e.target == "e1"
    assert e.duration_ms == 1000


def test_ambient_mumble_event():
    e = AmbientEvent(npc_id="e2", event="mumble", text="hello", duration_ms=3000)
    assert e.text == "hello"
    assert e.duration_ms == 3000


def test_ambient_invalid_event_rejected():
    with pytest.raises(ValidationError):
        AmbientEvent(npc_id="e1", event="fly", duration_ms=100)
