"""ChatOrchestrator: ties together LLM, TTS, and ContextManager for chat."""
from __future__ import annotations

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
    ) -> AsyncGenerator[dict, None]:
        """Run a full chat turn and yield streaming events.

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

            # 2. Build full messages list: system + history + user
            messages = [system_message, *context, {"role": "user", "content": user_message}]

            # 3. Stream from LLM, yield text_chunks, accumulate full text
            full_response = ""
            async for chunk in self._llm.generate_stream(messages):
                full_response += chunk
                yield {"type": "text_chunk", "content": chunk}

            # 4. Parse the accumulated response into 3 segments
            segments = self._parse_segments(full_response)

            # 5. Store the exchange in context
            self._context.add_turn(session_id, user_message, full_response)

            # 6. Trigger summarization (no-op if under limit)
            await self._context.summarize(session_id)

            # 7. Synthesize TTS audio for the speak segment
            audio_bytes = await self._tts.synthesize(segments.speak, voice="alloy")
            audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")

            # 8. Yield final result event
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
