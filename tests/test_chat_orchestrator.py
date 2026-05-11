"""Tests for app.services.chat_orchestrator.ChatOrchestrator."""
from __future__ import annotations

import pytest


class _StubLLM:
    """Stub LLMAdapter that records calls and returns/configurable chunks."""

    def __init__(self, response: str = "", raise_on_stream: bool = False) -> None:
        self._response = response
        self._raise_on_stream = raise_on_stream
        self.calls: list[list[dict]] = []

    async def generate(
        self,
        messages: list[dict],
        *,
        temperature: float = 0.7,
    ) -> str:
        self.calls.append(messages)
        return self._response

    async def generate_stream(
        self,
        messages: list[dict],
        *,
        temperature: float = 0.7,
    ) -> ...:
        self.calls.append(messages)
        if self._raise_on_stream:
            raise RuntimeError("LLM streaming failed")
        for i in range(0, len(self._response), 3):
            yield self._response[i : i + 3]


class _StubTTS:
    """Stub TTSAdapter that records calls and returns fake audio bytes."""

    def __init__(self, audio_bytes: bytes = b"fake_audio") -> None:
        self._audio = audio_bytes
        self.calls: list[tuple[str, str]] = []

    async def synthesize(
        self,
        text: str,
        *,
        voice: str = "alloy",
    ) -> bytes:
        self.calls.append((text, voice))
        return self._audio


class _StubContext:
    """Stub ContextManager that records calls for inspection."""

    def __init__(self, context: list[dict] | None = None) -> None:
        self.turns: list[tuple[str, str, str]] = []
        self._context = context or [
            {"role": "assistant", "content": "Previous conversation context here."}
        ]
        self.summarized: bool = False

    def add_turn(self, session_id: str, user_message: str, assistant_content: str) -> None:
        self.turns.append((session_id, user_message, assistant_content))

    def get_context(self, session_id: str) -> list[dict]:
        return list(self._context)

    async def summarize(self, session_id: str) -> str:
        self.summarized = True
        return "summary"

    def clear_session(self, session_id: str) -> None:
        self.turns = []


# ---------------------------------------------------------------------------
# Sample realistic XML response
# ---------------------------------------------------------------------------

_REALISTIC_RESPONSE: str = """\
<speak>Hello! How are you today?</speak>
<learning>Good job using greetings!</learning>
<followup>What would you like to talk about?</followup>"""


# ---------------------------------------------------------------------------
# Streaming chunks
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_chat_stream_yields_text_chunks() -> None:
    """LLM stream chunks are yielded as text_chunk events."""
    from app.services.chat_orchestrator import ChatOrchestrator

    llm = _StubLLM(response="Hello! How are you?")
    tts = _StubTTS()
    ctx = _StubContext()
    orch = ChatOrchestrator(llm=llm, tts=tts, context=ctx)

    events: list[dict] = []
    async for event in orch.chat_stream("s1", "Hi", {"role": "system", "content": "You are a bot."}):
        events.append(event)

    text_chunks = [e for e in events if e["type"] == "text_chunk"]
    assert len(text_chunks) > 0
    assert "".join(e["content"] for e in text_chunks) == "Hello! How are you?"


@pytest.mark.asyncio
async def test_chat_stream_yields_result_after_streaming() -> None:
    """After all text chunks, a result event is yielded."""
    from app.services.chat_orchestrator import ChatOrchestrator

    llm = _StubLLM(response="<speak>Hi</speak><learning></learning><followup></followup>")
    tts = _StubTTS()
    ctx = _StubContext()
    orch = ChatOrchestrator(llm=llm, tts=tts, context=ctx)

    events: list[dict] = []
    async for event in orch.chat_stream("s1", "Hi", {"role": "system", "content": "You are a bot."}):
        events.append(event)

    result_events = [e for e in events if e["type"] == "result"]
    assert len(result_events) == 1


# ---------------------------------------------------------------------------
# XML parsing
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_chat_stream_parses_segments() -> None:
    """Result event contains correctly parsed speak/learning/followup segments."""
    from app.services.chat_orchestrator import ChatOrchestrator

    llm = _StubLLM(response=_REALISTIC_RESPONSE)
    tts = _StubTTS()
    ctx = _StubContext()
    orch = ChatOrchestrator(llm=llm, tts=tts, context=ctx)

    result_event = None
    async for event in orch.chat_stream("s1", "Hi", {"role": "system", "content": "You are a bot."}):
        if event["type"] == "result":
            result_event = event

    assert result_event is not None
    segments = result_event["segments"]
    assert segments["speak"] == "Hello! How are you today?"
    assert segments["learning"] == "Good job using greetings!"
    assert segments["followup"] == "What would you like to talk about?"
    assert "audio_base64" in result_event


@pytest.mark.asyncio
async def test_chat_stream_handles_missing_tags_gracefully() -> None:
    """Response with no XML tags results in empty segment strings."""
    from app.services.chat_orchestrator import ChatOrchestrator

    llm = _StubLLM(response="This is a plain text response with no XML tags.")
    tts = _StubTTS()
    ctx = _StubContext()
    orch = ChatOrchestrator(llm=llm, tts=tts, context=ctx)

    result_event = None
    async for event in orch.chat_stream("s1", "Hi", {"role": "system", "content": "You are a bot."}):
        if event["type"] == "result":
            result_event = event

    assert result_event is not None
    segments = result_event["segments"]
    assert segments["speak"] == ""
    assert segments["learning"] == ""
    assert segments["followup"] == ""


# ---------------------------------------------------------------------------
# Side effects
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_chat_stream_stores_turn_in_context() -> None:
    """add_turn is called with correct session_id, user message, and full response."""
    from app.services.chat_orchestrator import ChatOrchestrator

    response_text = "<speak>Hello!</speak><learning>Tip</learning><followup>Q?</followup>"
    llm = _StubLLM(response=response_text)
    tts = _StubTTS()
    ctx = _StubContext()
    orch = ChatOrchestrator(llm=llm, tts=tts, context=ctx)

    async for _ in orch.chat_stream("s1", "Hi there", {"role": "system", "content": "You are a bot."}):
        pass

    assert len(ctx.turns) == 1
    sid, user_msg, assistant_content = ctx.turns[0]
    assert sid == "s1"
    assert user_msg == "Hi there"
    assert assistant_content == response_text


@pytest.mark.asyncio
async def test_chat_stream_synthesizes_tts() -> None:
    """TTS is called with the speak segment text and the default voice."""
    from app.services.chat_orchestrator import ChatOrchestrator

    llm = _StubLLM(
        response="<speak>Hello world!</speak><learning></learning><followup></followup>"
    )
    tts = _StubTTS()
    ctx = _StubContext()
    orch = ChatOrchestrator(llm=llm, tts=tts, context=ctx)

    async for _ in orch.chat_stream("s1", "Hi", {"role": "system", "content": "You are a bot."}):
        pass

    assert len(tts.calls) == 1
    text, voice = tts.calls[0]
    assert text == "Hello world!"
    assert voice == "alloy"


@pytest.mark.asyncio
async def test_chat_stream_calls_summarize() -> None:
    """summarize is called on the context manager at the end of each turn."""
    from app.services.chat_orchestrator import ChatOrchestrator

    llm = _StubLLM(response="<speak>Hi</speak><learning></learning><followup></followup>")
    tts = _StubTTS()
    ctx = _StubContext()
    orch = ChatOrchestrator(llm=llm, tts=tts, context=ctx)

    async for _ in orch.chat_stream("s1", "Hi", {"role": "system", "content": "You are a bot."}):
        pass

    assert ctx.summarized is True


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_error_during_streaming() -> None:
    """When LLM streaming raises, an error event is yielded (no crash)."""
    from app.services.chat_orchestrator import ChatOrchestrator

    llm = _StubLLM(response="", raise_on_stream=True)
    tts = _StubTTS()
    ctx = _StubContext()
    orch = ChatOrchestrator(llm=llm, tts=tts, context=ctx)

    events: list[dict] = []
    async for event in orch.chat_stream("s1", "Hi", {"role": "system", "content": "You are a bot."}):
        events.append(event)

    error_events = [e for e in events if e["type"] == "error"]
    result_events = [e for e in events if e["type"] == "result"]

    assert len(error_events) == 1
    assert "LLM streaming failed" in error_events[0]["message"]
    assert len(result_events) == 0  # No result on failure


@pytest.mark.asyncio
async def test_chat_stream_prepends_learner_context_message() -> None:
    """When a learner_context_message is supplied, it is the first message sent to the LLM."""
    from app.services.chat_orchestrator import ChatOrchestrator

    llm = _StubLLM(response="<speak>Hi</speak><learning></learning><followup></followup>")
    tts = _StubTTS()
    ctx = _StubContext(context=[{"role": "assistant", "content": "prior"}])
    orch = ChatOrchestrator(llm=llm, tts=tts, context=ctx)

    learner_ctx = {"role": "system", "content": "Learner is at intermediate."}
    system = {"role": "system", "content": "You are a persona."}

    async for _ in orch.chat_stream("s1", "Hi", system, learner_context_message=learner_ctx):
        pass

    sent = llm.calls[0]
    assert sent[0] == learner_ctx
    assert sent[1] == system
    assert sent[-1] == {"role": "user", "content": "Hi"}


@pytest.mark.asyncio
async def test_chat_stream_omits_learner_context_when_none() -> None:
    """When no learner_context_message is supplied, the system message is first."""
    from app.services.chat_orchestrator import ChatOrchestrator

    llm = _StubLLM(response="<speak>Hi</speak><learning></learning><followup></followup>")
    tts = _StubTTS()
    ctx = _StubContext(context=[])
    orch = ChatOrchestrator(llm=llm, tts=tts, context=ctx)

    system = {"role": "system", "content": "You are a persona."}
    async for _ in orch.chat_stream("s1", "Hi", system):
        pass

    sent = llm.calls[0]
    assert sent[0] == system


@pytest.mark.asyncio
async def test_chat_stream_emits_audio_before_result() -> None:
    """`audio` event arrives before the final `result` event so the client
    can begin playback while the orchestrator finishes packaging segments."""
    from app.services.chat_orchestrator import ChatOrchestrator

    llm = _StubLLM(response=_REALISTIC_RESPONSE)
    tts = _StubTTS()
    ctx = _StubContext(context=[])
    orch = ChatOrchestrator(llm=llm, tts=tts, context=ctx)

    types: list[str] = []
    async for event in orch.chat_stream("s1", "Hi", {"role": "system", "content": "x"}):
        types.append(event["type"])

    assert "audio" in types
    assert "result" in types
    assert types.index("audio") < types.index("result")
    # speak_text is emitted as soon as </speak> closes during streaming
    assert "speak_text" in types
    assert types.index("speak_text") < types.index("audio")


@pytest.mark.asyncio
async def test_chat_stream_speak_text_carries_speak_segment() -> None:
    from app.services.chat_orchestrator import ChatOrchestrator

    llm = _StubLLM(response=_REALISTIC_RESPONSE)
    tts = _StubTTS()
    ctx = _StubContext(context=[])
    orch = ChatOrchestrator(llm=llm, tts=tts, context=ctx)

    speak_event = None
    async for event in orch.chat_stream("s1", "Hi", {"role": "system", "content": "x"}):
        if event["type"] == "speak_text":
            speak_event = event
            break

    assert speak_event is not None
    assert speak_event["content"] == "Hello! How are you today?"
