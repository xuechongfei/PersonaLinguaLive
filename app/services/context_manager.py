"""ContextManager: per-session sliding window with LLM summarization."""
from __future__ import annotations

from app.adapters.llm.base import LLMAdapter


class ContextManager:
    """Manages conversation context with a sliding window and summarization.

    Each session maintains a list of message exchanges. When the window
    exceeds *max_exchanges* pairs, the oldest messages are condensed into
    a summary via the LLM.
    """

    def __init__(
        self,
        llm: LLMAdapter,
        *,
        max_exchanges: int = 10,
    ) -> None:
        self._llm = llm
        self._max_exchanges = max_exchanges
        self._sessions: dict[str, list[dict]] = {}
        self._summaries: dict[str, str] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add_turn(
        self,
        session_id: str,
        user_message: str,
        assistant_content: str,
    ) -> None:
        """Append a user/assistant exchange to the session."""
        if session_id not in self._sessions:
            self._sessions[session_id] = []

        self._sessions[session_id].append(
            {"role": "user", "content": user_message}
        )
        self._sessions[session_id].append(
            {"role": "assistant", "content": assistant_content}
        )

    def get_context(self, session_id: str) -> list[dict]:
        """Return the conversation context suitable for LLM consumption.

        Prepends a summary system message if one exists, then returns the
        last ``max_exchanges * 2`` messages.  Returns an empty list when
        the session does not exist.
        """
        if session_id not in self._sessions:
            return []

        messages = list(self._sessions[session_id])

        # Sliding-window trim
        max_messages = self._max_exchanges * 2
        if len(messages) > max_messages:
            messages = messages[-max_messages:]

        # Prepend stored summary when available
        summary = self._summaries.get(session_id)
        if summary:
            messages = [
                {"role": "system", "content": f"Previous conversation summary: {summary}"},
                *messages,
            ]

        return messages

    async def summarize(self, session_id: str) -> str:
        """Summarise old messages when the session exceeds the window limit.

        If the session has more than ``max_exchanges * 2`` messages the
        oldest ones are sent to the LLM for condensation.  The summary is
        stored and returned; the summarised messages are removed from the
        active window.

        Returns the existing summary when the window is still within the
        limit, or an empty string when no summary exists yet.
        """
        if session_id not in self._sessions:
            return ""

        messages = self._sessions[session_id]
        max_messages = self._max_exchanges * 2

        if len(messages) <= max_messages:
            return self._summaries.get(session_id, "")

        # Split: oldest messages get summarised, keep the most recent ones
        to_summarize = messages[:-max_messages]
        self._sessions[session_id] = messages[-max_messages:]

        prompt: list[dict] = [
            {
                "role": "system",
                "content": (
                    "Summarize this English learning conversation concisely. "
                    "Include topics discussed, vocabulary used, and the user's "
                    "approximate level."
                ),
            },
            {
                "role": "user",
                "content": "\n".join(
                    f"{m['role']}: {m['content']}" for m in to_summarize
                ),
            },
        ]

        summary_text = await self._llm.generate(prompt, temperature=0.3)
        self._summaries[session_id] = summary_text
        return summary_text

    def clear_session(self, session_id: str) -> None:
        """Remove all stored data for a session."""
        self._sessions.pop(session_id, None)
        self._summaries.pop(session_id, None)
