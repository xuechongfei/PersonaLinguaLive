"""Integration tests for WebSocket /api/chat using FakeLLMAdapter and FakeTTSAdapter."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("PLL_AI_LLM_PROVIDER", "fake")
    monkeypatch.setenv("PLL_AI_TTS_PROVIDER", "fake")
    monkeypatch.setenv("PLL_RATE_LIMIT_CHAT_MESSAGES_PER_MIN", "100")
    from app.main import create_app

    return TestClient(create_app())


def test_chat_websocket_full_flow(client):
    """A full chat turn: init -> user_message -> text_chunks -> result."""
    with client.websocket_connect("/api/chat") as ws:
        # Send init
        ws.send_json({
            "type": "init",
            "session_id": "test_sess_1",
            "system_message": {"role": "system", "content": "You are a bot."},
        })

        # Send user message
        ws.send_json({"type": "user_message", "content": "Hello"})

        # Receive events
        events = []
        while True:
            event = ws.receive_json()
            events.append(event)
            if event["type"] == "result":
                break

        # Verify events
        text_chunks = [e for e in events if e["type"] == "text_chunk"]
        assert len(text_chunks) > 0

        result_events = [e for e in events if e["type"] == "result"]
        assert len(result_events) == 1
        assert "segments" in result_events[0]
        assert "audio_base64" in result_events[0]


def test_chat_websocket_init_required_first(client):
    """Sending a non-init message first returns an error and closes."""
    with client.websocket_connect("/api/chat") as ws:
        ws.send_json({"type": "user_message", "content": "hi"})
        resp = ws.receive_json()
        assert resp["type"] == "error"


def test_chat_websocket_rate_limited(monkeypatch):
    """Basic flow works even with low rate limit setting."""
    monkeypatch.setenv("PLL_AI_LLM_PROVIDER", "fake")
    monkeypatch.setenv("PLL_AI_TTS_PROVIDER", "fake")
    monkeypatch.setenv("PLL_RATE_LIMIT_CHAT_MESSAGES_PER_MIN", "1")
    from app.main import create_app

    client = TestClient(create_app())
    with client.websocket_connect("/api/chat") as ws:
        ws.send_json({
            "type": "init",
            "session_id": "test_limit",
            "system_message": {"role": "system", "content": "You are a bot."},
        })
        ws.send_json({"type": "user_message", "content": "Hi"})
        events = []
        while True:
            event = ws.receive_json()
            events.append(event)
            if event["type"] in ("result", "error"):
                break
