from __future__ import annotations

from app.services.context_manager import ContextManager


class FakeLLM:
    async def generate(self, messages, *, temperature=0.0):
        return "summary"


def test_context_separate_by_npc():
    cm = ContextManager(FakeLLM())
    cm.add_turn(("s1", "npc_a"), "hi", "hello back")
    cm.add_turn(("s1", "npc_b"), "hey", "hey there")
    ctx_a = cm.get_context(("s1", "npc_a"))
    ctx_b = cm.get_context(("s1", "npc_b"))
    assert len(ctx_a) == 2
    assert len(ctx_b) == 2
    assert ctx_a[1]["content"] == "hello back"
    assert ctx_b[1]["content"] == "hey there"


def test_string_key_backward_compat():
    cm = ContextManager(FakeLLM())
    cm.add_turn("old_session", "hi", "hi")
    ctx = cm.get_context("old_session")
    assert len(ctx) == 2


def test_streaming_flag():
    cm = ContextManager(FakeLLM())
    cm.set_streaming("s1", True)
    assert cm.is_streaming("s1") is True
    cm.set_streaming("s1", False)
    assert cm.is_streaming("s1") is False


def test_streaming_flag_per_npc():
    cm = ContextManager(FakeLLM())
    cm.set_streaming(("s1", "npc_a"), True)
    cm.set_streaming(("s1", "npc_b"), False)
    assert cm.is_streaming(("s1", "npc_a")) is True
    assert cm.is_streaming(("s1", "npc_b")) is False
