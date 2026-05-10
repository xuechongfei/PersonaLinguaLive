"""FakeLLMAdapter: deterministic stub for tests + offline development."""
from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from typing import Any

_FAKE_PERSONA_RESPONSE: str = json.dumps(
    {
        "persona_name": "Tilly the Teacup",
        "personality_description": "A cheerful little teacup who loves morning gossip and knows everything about tea.",
        "persona_appearance": "White porcelain with blue floral pattern, steam swirling gently from the top.",
        "system_prompt": "You are Tilly the Teacup, a cheerful and talkative teacup. You love chatting about tea, mornings, and cozy kitchens. You always respond in warm, friendly English. Keep responses short and conversational.",
        "vocab_focus": ["teacup", "saucer", "brew", "steep", "aroma"],
    }
)

_FAKE_CHAT_RESPONSE: str = (
    "<speak>Hello there! I'm so happy you picked me to talk to!</speak>"
    "<learning>**New word:** 'teacup' - a small cup for drinking tea.</learning>"
    "<followup>Try saying: What do you like most about being a teacup?</followup>"
)

_FAKE_SUMMARY_RESPONSE: str = json.dumps(
    {
        "new_words": ["teacup", "saucer", "brew"],
        "grammar_points": ["Present simple for describing routines"],
        "fluency_score": 7,
        "strengths": ["Good vocabulary", "Clear pronunciation"],
        "areas_to_improve": ["Past tense usage"],
    }
)


class FakeLLMAdapter:
    def __init__(self) -> None:
        self.last_messages: list[dict] | None = None

    async def generate(
        self,
        messages: list[dict],
        *,
        temperature: float = 0.7,
    ) -> str:
        self.last_messages = messages
        system = messages[0]["content"] if messages else ""
        if "persona" in system.lower():
            return _FAKE_PERSONA_RESPONSE
        if "summary" in system.lower() or "conversation" in system.lower():
            return _FAKE_SUMMARY_RESPONSE
        return _FAKE_CHAT_RESPONSE

    async def generate_stream(
        self,
        messages: list[dict],
        *,
        temperature: float = 0.7,
    ) -> AsyncGenerator[str, None]:
        self.last_messages = messages
        text = await self.generate(messages, temperature=temperature)
        for token in _tokenize(text):
            yield token


def _tokenize(text: str) -> list[str]:
    """Split text into ~1-3 character tokens for realistic streaming."""
    tokens: list[str] = []
    i = 0
    while i < len(text):
        size = (hash(text[i : i + 1]) % 3) + 1  # deterministic 1-3 chars
        tokens.append(text[i : i + size])
        i += size
    return tokens
