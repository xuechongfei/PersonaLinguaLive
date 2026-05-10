"""Tests for summary prompt and POST /api/chat/summary endpoint."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


def test_build_summary_messages():
    """Verify summary prompt structure."""
    from app.prompts.chat_summary import build_summary_messages

    messages = build_summary_messages("user: hello\nassistant: hi there", "beginner")
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    assert "new_words" in messages[0]["content"]
    assert "fluency_score" in messages[0]["content"]
    assert "hello" in messages[1]["content"]


def test_empty_summary_when_no_session(client):
    """Returns default ChatSummaryResponse when session not found."""
    resp = client.post("/api/chat/summary", json={
        "session_id": "nonexistent",
        "user_level": "beginner",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["new_words"] == []
    assert body["fluency_score"] == 5


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("PLL_AI_LLM_PROVIDER", "fake")
    monkeypatch.setenv("PLL_RATE_LIMIT_CHAT_MESSAGES_PER_MIN", "100")
    from app.main import create_app
    return TestClient(create_app())


def test_summary_with_conversation(client):
    """After a chat WebSocket session, summary returns learning insights."""
    # First, have a chat session to populate context
    with client.websocket_connect("/api/chat") as ws:
        ws.send_json({
            "type": "init",
            "session_id": "summ_sess_1",
            "system_message": {"role": "system", "content": "You are a bot."},
        })
        ws.send_json({"type": "user_message", "content": "Hello!"})
        # Consume all events until result
        while True:
            event = ws.receive_json()
            if event["type"] == "result":
                break

    # Now call summary
    resp = client.post("/api/chat/summary", json={
        "session_id": "summ_sess_1",
        "user_level": "beginner",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert "new_words" in body
    assert "grammar_points" in body
    assert "fluency_score" in body
    assert "strengths" in body
    assert "areas_to_improve" in body
