"""Integration test for ambient events multiplexed through chat WS."""
from __future__ import annotations

import pytest


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("PLL_AI_LLM_PROVIDER", "fake")
    monkeypatch.setenv("PLL_AI_TTS_PROVIDER", "fake")
    monkeypatch.setenv("PLL_AI_VISION_PROVIDER", "fake")
    monkeypatch.setenv("PLL_AI_IMAGEGEN_PROVIDER", "fake")
    monkeypatch.setenv("PLL_RATE_LIMIT_CHAT_MESSAGES_PER_MIN", "100")
    from fastapi.testclient import TestClient

    from app.main import create_app
    return TestClient(create_app())


def test_chat_with_world_id_and_npc_id(client):
    """Chat WS init frame can include world_id and npc_id."""
    with client.websocket_connect("/api/chat") as ws:
        ws.send_json({
            "type": "init",
            "session_id": "s1",
            "system_message": {"role": "system", "content": "You are a bot."},
            "world_id": "",
            "npc_id": "",
        })
        ws.send_json({"type": "user_message", "content": "Hello"})
        events = []
        while True:
            event = ws.receive_json()
            events.append(event)
            if event["type"] == "result":
                break
        assert len(events) > 0
        assert events[-1]["type"] == "result"
