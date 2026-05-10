"""Tests for app.services.context_manager.ContextManager."""
from __future__ import annotations

import pytest


class _StubAdapter:
    """Stub LLMAdapter that records calls and returns a configurable response."""

    def __init__(self, response: str = "") -> None:
        self._response = response
        self.calls: list[list[dict]] = []

    async def generate(
        self,
        messages: list[dict],
        *,
        temperature: float = 0.7,
    ) -> str:
        self.calls.append(messages)
        return self._response


# ---------------------------------------------------------------------------
# add_turn / get_context
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_add_turn_stores_messages() -> None:
    """Adding a turn stores user and assistant messages with correct roles."""
    from app.services.context_manager import ContextManager

    adapter = _StubAdapter()
    cm = ContextManager(adapter, max_exchanges=10)

    cm.add_turn("sess1", "Hello", "Hi there!")

    ctx = cm.get_context("sess1")
    assert len(ctx) == 2
    assert ctx[0] == {"role": "user", "content": "Hello"}
    assert ctx[1] == {"role": "assistant", "content": "Hi there!"}


@pytest.mark.asyncio
async def test_get_context_returns_empty_for_unknown_session() -> None:
    """get_context returns an empty list for a non-existent session."""
    from app.services.context_manager import ContextManager

    adapter = _StubAdapter()
    cm = ContextManager(adapter)

    assert cm.get_context("nonexistent") == []


# ---------------------------------------------------------------------------
# Summarisation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_summarize_triggers_when_over_limit() -> None:
    """When messages exceed max_exchanges*2 the LLM is called to summarise."""
    from app.services.context_manager import ContextManager

    adapter = _StubAdapter(response="Concise summary.")
    cm = ContextManager(adapter, max_exchanges=10)

    # 12 exchanges = 24 messages, which exceeds max_exchanges*2 = 20
    for i in range(12):
        cm.add_turn("sess1", f"user msg {i}", f"assistant msg {i}")

    result = await cm.summarize("sess1")

    assert result == "Concise summary."
    assert len(adapter.calls) == 1  # LLM called exactly once

    # Only 20 messages should remain in internal storage
    assert len(cm._sessions["sess1"]) == 20  # type: ignore[attr-defined]

    # get_context returns 20 messages + 1 system summary = 21 entries
    ctx = cm.get_context("sess1")
    assert len(ctx) == 21

    # Summary is prepended as a system message
    assert ctx[0] == {
        "role": "system",
        "content": "Previous conversation summary: Concise summary.",
    }

    # The oldest 2 exchanges (4 messages) were summarised away;
    # the remaining window starts from exchange index 2.
    assert ctx[1] == {"role": "user", "content": "user msg 2"}
    assert ctx[2] == {"role": "assistant", "content": "assistant msg 2"}


@pytest.mark.asyncio
async def test_summarize_does_not_run_when_under_limit() -> None:
    """When messages are within the window limit, the LLM is not called."""
    from app.services.context_manager import ContextManager

    adapter = _StubAdapter()
    cm = ContextManager(adapter, max_exchanges=10)

    for i in range(5):
        cm.add_turn("sess1", f"user msg {i}", f"assistant msg {i}")

    result = await cm.summarize("sess1")

    assert result == ""  # No summary exists yet
    assert len(adapter.calls) == 0  # LLM was NOT called

    # All 10 messages are preserved
    ctx = cm.get_context("sess1")
    assert len(ctx) == 10


@pytest.mark.asyncio
async def test_context_includes_summary_after_summarize() -> None:
    """After summarisation, get_context prepends the summary as a system message."""
    from app.services.context_manager import ContextManager

    adapter = _StubAdapter(response="Session summary.")
    cm = ContextManager(adapter, max_exchanges=10)

    for i in range(12):
        cm.add_turn("sess1", f"user msg {i}", f"assistant msg {i}")

    await cm.summarize("sess1")

    ctx = cm.get_context("sess1")

    # First entry is the summary system message
    assert ctx[0]["role"] == "system"
    assert "Session summary." in ctx[0]["content"]


# ---------------------------------------------------------------------------
# Session lifecycle
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_clear_session_removes_data() -> None:
    """clear_session removes all data for the given session."""
    from app.services.context_manager import ContextManager

    adapter = _StubAdapter(response="summary")
    cm = ContextManager(adapter, max_exchanges=10)

    # Populate session and trigger summarisation so both messages and
    # summaries are populated.
    for i in range(12):
        cm.add_turn("sess1", f"user msg {i}", f"assistant msg {i}")
    await cm.summarize("sess1")

    assert len(adapter.calls) == 1  # sanity: summarisation happened
    assert len(cm.get_context("sess1")) == 21  # sanity: session has data

    cm.clear_session("sess1")

    assert cm.get_context("sess1") == []


@pytest.mark.asyncio
async def test_multiple_sessions_independent() -> None:
    """Sessions with different IDs do not interfere with each other."""
    from app.services.context_manager import ContextManager

    adapter = _StubAdapter()
    cm = ContextManager(adapter)

    cm.add_turn("sess1", "Hello from 1", "Hi 1")
    cm.add_turn("sess2", "Hello from 2", "Hi 2")
    cm.add_turn("sess1", "Second msg 1", "Second reply 1")

    ctx1 = cm.get_context("sess1")
    ctx2 = cm.get_context("sess2")

    assert len(ctx1) == 4   # 2 exchanges = 4 messages
    assert len(ctx2) == 2   # 1 exchange  = 2 messages

    assert ctx1[0] == {"role": "user", "content": "Hello from 1"}
    assert ctx1[1] == {"role": "assistant", "content": "Hi 1"}
    assert ctx2[0] == {"role": "user", "content": "Hello from 2"}
    assert ctx2[1] == {"role": "assistant", "content": "Hi 2"}
