"""LLMAdapter Protocol for text-generation LLMs."""
from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Protocol


class LLMAdapter(Protocol):
    """Provider-agnostic interface for text-generation LLMs."""

    async def generate(
        self,
        messages: list[dict],
        *,
        temperature: float = 0.7,
    ) -> str:
        """Non-streaming: return complete response string."""
        ...

    async def generate_stream(
        self,
        messages: list[dict],
        *,
        temperature: float = 0.7,
    ) -> AsyncGenerator[str, None]:
        """Streaming: yield content tokens as they arrive."""
        ...
        # Pragmatic: return empty generator so Protocol check passes
        if False:
            yield ""
