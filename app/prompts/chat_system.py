"""Prompt templates for chat system message and 3-segment response."""
from __future__ import annotations


def build_chat_system_message(
    persona_name: str,
    persona_description: str,
    persona_prompt: str,
    user_level: str = "beginner",
) -> dict:
    """Build the system message for a chat session with a persona."""
    level_instructions = {
        "beginner": (
            "Use very simple sentences and basic vocabulary. "
            "Speak slowly and clearly. Repeat key words."
        ),
        "intermediate": (
            "Use moderate vocabulary and natural sentence structures. "
            "Occasionally introduce new useful words."
        ),
        "advanced": (
            "Use natural, fluent English as you would with another fluent speaker. "
            "Focus on nuanced expressions and idioms when appropriate."
        ),
    }
    level_instr = level_instructions.get(user_level, level_instructions["intermediate"])

    content = (
        f"You are {persona_name}. {persona_description}\n\n"
        f"Personality and voice: {persona_prompt}\n\n"
        f"User level ({user_level}): {level_instr}\n\n"
        "You MUST format EVERY response with these XML tags:\n"
        "<speak>The text that will be spoken aloud. Keep it conversational.</speak>\n"
        "<learning>English learning tips: new vocabulary, grammar points, or corrections.</learning>\n"
        "<followup>A follow-up question to keep the conversation going.</followup>\n\n"
        "Rules:\n"
        "- Always respond in English\n"
        "- <speak> must be at least 1 sentence\n"
        "- <learning> can be empty if no teaching point applies\n"
        "- <followup> should be a natural question related to the conversation\n"
        "- Keep total response under 5 sentences\n"
        "- Stay in character as the object\n"
        "- Be encouraging and positive"
    )
    return {"role": "system", "content": content}


def build_chat_history_messages(context: list[dict]) -> list[dict]:
    """Build history messages from context manager output."""
    return [msg for msg in context if msg["role"] in ("user", "assistant")]
