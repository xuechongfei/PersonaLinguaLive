"""FakeLLMAdapter: deterministic stub for tests + offline development."""
from __future__ import annotations

import json
from collections.abc import AsyncGenerator

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
        "new_words": [
            {"word": "teacup", "definition": "small cup for tea", "example": "I sip from a teacup."},
            {"word": "saucer", "definition": "small plate under a cup", "example": "Place the cup on a saucer."},
            {"word": "brew", "definition": "to make tea or coffee", "example": "Let the tea brew for two minutes."},
        ],
        "grammar_points": ["Present simple for describing routines"],
        "fluency_score": 7,
        "strengths": ["Good vocabulary", "Clear pronunciation"],
        "areas_to_improve": ["Past tense usage"],
    }
)

_FAKE_SCENE_BIBLE_RESPONSE: str = json.dumps(
    {
        "world": {
            "place": "cozy kitchen",
            "time_of_day": "morning",
            "weather": "sunny",
            "mood": "warm",
            "ambient_sounds": ["kitchen_sizzle", "water_pouring"],
            "bgm_mood": "warm",
            "art_style_prompt": "soft watercolor cartoon, warm palette",
        },
        "npcs": [
            {
                "entity_id": "e1",
                "kind": "object",
                "persona_name": "Tilly",
                "role_in_scene": "a cheerful teacup on the counter",
                "relationship_to_user": "your morning companion",
                "personality": "warm and talkative, loves gossip",
                "voice_traits": {"gender": "female", "age": "adult", "tone": "warm"},
                "vocab_focus": ["teacup", "brew", "steam", "aroma"],
                "ambient_actions": ["steams gently", "clinks softly"],
            },
            {
                "entity_id": "e2",
                "kind": "object",
                "persona_name": "Chester",
                "role_in_scene": "a sturdy wooden chair",
                "personality": "reliable and thoughtful",
                "voice_traits": {"gender": "male", "age": "adult", "tone": "gruff"},
                "vocab_focus": ["sturdy", "support", "rest"],
                "ambient_actions": ["creaks slightly", "shifts weight"],
            },
        ],
        "cross_relationships": [
            {"from_entity": "e1", "to_entity": "e2", "note": "often sit together at breakfast"},
        ],
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
        if "world builder" in system.lower() or "scene bible" in system.lower():
            return _FAKE_SCENE_BIBLE_RESPONSE
        if "persona_name" in system.lower() or "Persona name" in system:
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
