"""ChatOrchestrator: ties together LLM, TTS, and ContextManager for chat."""
from __future__ import annotations

import asyncio
import base64
import re
from collections.abc import AsyncGenerator

from app.adapters.llm.base import LLMAdapter
from app.adapters.tts.base import TTSAdapter
from app.prompts.chat_system import build_chat_system_message_world
from app.schemas.chat import ChatSegment
from app.schemas.world import SceneBible
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
        *,
        learner_context_message: dict | None = None,
        voice_id: str | None = None,
        scene_bible: SceneBible | None = None,
        npc_id: str = "",
    ) -> AsyncGenerator[dict, None]:
        """Run a full chat turn and yield streaming events.

        ``learner_context_message`` (optional) is prepended to the message list
        so the LLM can recycle vocab and stay calibrated to the learner.

        ``voice_id`` (optional) is the MiniMax voice ID to use for TTS. If
        omitted the adapter's default voice (usually "alloy") is used.

        ``scene_bible`` (optional) switches to Living Scene mode — the system
        message is built from the SceneBible for the given npc_id.

        ``npc_id`` (optional) identifies which NPC the user is talking to,
        used to partition context per-NPC.

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
            # Determine effective session key for per-NPC context isolation
            effective_key: str | tuple = (session_id, npc_id) if npc_id else session_id
            effective_voice = voice_id or "alloy"

            # 1. Get existing context
            context = self._context.get_context(effective_key)

            # 2. Build effective system message
            if scene_bible is not None and npc_id:
                npc = next(
                    (n for n in scene_bible.npcs if n.entity_id == npc_id), None
                )
                if npc is not None:
                    persona_name = npc.persona_name
                    effective_system = build_chat_system_message_world(
                        persona_name=persona_name,
                        active_npc=npc,
                        bible=scene_bible,
                        user_level="beginner",
                    )
                else:
                    effective_system = system_message
            else:
                effective_system = system_message

            # 3. Build full messages list: [learner_ctx?] + system + history + user
            preface: list[dict] = []
            if learner_context_message is not None:
                preface.append(learner_context_message)
            messages = [
                *preface,
                effective_system,
                *context,
                {"role": "user", "content": user_message},
            ]

            # 4. Set streaming flag
            self._context.set_streaming(effective_key, True)

            try:
                # 5. Stream from LLM, yield text_chunks, accumulate full text.
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
                            self._tts.synthesize(speak_text, voice=effective_voice)
                        )
                        speak_text_emitted = True

                # 6. Parse the accumulated response into 3 segments
                segments = self._parse_segments(full_response)

                # 7. Store the exchange in context
                self._context.add_turn(effective_key, user_message, full_response)

                # 8. Trigger summarization (no-op if under limit)
                await self._context.summarize(effective_key)

                # 9. If we never saw </speak> mid-stream, synthesize now
                if tts_task is None:
                    audio_bytes = await self._tts.synthesize(segments.speak, voice=effective_voice)
                else:
                    audio_bytes = await tts_task
                audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")

                # 10. Emit audio and result
                yield {"type": "audio", "audio_base64": audio_base64}
                yield {
                    "type": "result",
                    "segments": segments.model_dump(),
                    "audio_base64": audio_base64,
                }
            finally:
                self._context.set_streaming(effective_key, False)

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
