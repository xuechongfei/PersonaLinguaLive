"""ChatOrchestrator: ties together LLM, TTS, and ContextManager for chat."""
from __future__ import annotations

import asyncio
import base64
import re
from collections.abc import AsyncGenerator

from app.adapters.llm.base import LLMAdapter
from app.adapters.tts.base import TTSAdapter
from app.schemas.chat import ChatSegment
from app.services.context_manager import ContextManager


class ChatOrchestrator:
    """Orchestrates a full chat turn: LLM streaming -> XML parsing -> TTS."""

    def __init__(
        self,
        llm: LLMAdapter,
        tts: TTSAdapter,
        context: ContextManager,
    ) -> None:
        self._llm = llm
        self._tts = tts
        self._context = context

    async def chat_stream(
        self,
        session_id: str,
        user_message: str,
        system_message: dict,  # The persona system message from build_chat_system_message()
        learner_context_message: dict | None = None,
    ) -> AsyncGenerator[dict, None]:
        """Run a full chat turn and yield streaming events.

        ``learner_context_message`` (optional) is prepended to the message list
        so the LLM can recycle vocab and stay calibrated to the learner.

        Yields dict events of three types:

        ``text_chunk``
            Partial streaming text from the LLM::

                {"type": "text_chunk", "content": str}

        ``result``
            Final result with parsed segments and audio::

                {"type": "result",
                 "segments": {"speak": str, "learning": str, "followup": str},
                 "audio_base64": str}

        ``error``
            Any exception caught during processing::

                {"type": "error", "message": str}
        """
        try:
            # 1. Get existing context
            context = self._context.get_context(session_id)

            # 2. Build full messages list: [learner_ctx?] + system + history + user
            preface: list[dict] = []
            if learner_context_message is not None:
                preface.append(learner_context_message)
            messages = [
                *preface,
                system_message,
                *context,
                {"role": "user", "content": user_message},
            ]

            # 3. Stream from LLM, yield text_chunks, accumulate full text.
            #    The first time </speak> appears, kick off TTS in the background
            #    so audio can begin generating while learning/followup still stream.
            full_response = ""
            tts_task: asyncio.Task[bytes] | None = None
            speak_text_emitted = False
            async for chunk in self._llm.generate_stream(messages):
                full_response += chunk
                yield {"type": "text_chunk", "content": chunk}

                if not speak_text_emitted and "</speak>" in full_response:
                    speak_text = self._extract_tag(full_response, "speak")
                    yield {"type": "speak_text", "content": speak_text}
                    tts_task = asyncio.create_task(
                        self._tts.synthesize(speak_text, voice="alloy")
                    )
                    speak_text_emitted = True

            # 4. Parse the accumulated response into 3 segments
            segments = self._parse_segments(full_response)

            # 5. Store the exchange in context
            self._context.add_turn(session_id, user_message, full_response)

            # 6. Trigger summarization (no-op if under limit)
            await self._context.summarize(session_id)

            # 7. If we never saw </speak> mid-stream (e.g. response had no tag),
            #    synthesize now with whatever speak text we parsed.
            if tts_task is None:
                audio_bytes = await self._tts.synthesize(segments.speak, voice="alloy")
            else:
                audio_bytes = await tts_task
            audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")

            # 8. Emit audio as its own event so the client can begin playback
            #    immediately, then the final result for parsed segments.
            yield {"type": "audio", "audio_base64": audio_base64}
            yield {
                "type": "result",
                "segments": segments.model_dump(),
                "audio_base64": audio_base64,
            }

        except Exception as exc:
            yield {"type": "error", "message": str(exc)}

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_tag(text: str, tag: str) -> str:
        """Extract content of a single XML tag, or return empty string."""
        match = re.search(f"<{tag}>(.*?)</{tag}>", text, re.DOTALL)
        return match.group(1).strip() if match else ""

    @classmethod
    def _parse_segments(cls, text: str) -> ChatSegment:
        """Parse a 3-segment XML response into a ChatSegment."""
        return ChatSegment(
            speak=cls._extract_tag(text, "speak"),
            learning=cls._extract_tag(text, "learning"),
            followup=cls._extract_tag(text, "followup"),
        )
