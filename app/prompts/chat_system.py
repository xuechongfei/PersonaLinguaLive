"""Prompt templates for chat system message and 3-segment response."""
from __future__ import annotations

from app.schemas.world import NPCSpec, SceneBible


def build_chat_system_message_world(
    persona_name: str,
    active_npc: NPCSpec,
    bible: SceneBible,
    user_level: str = "beginner",
) -> dict:
    """Build system message using SceneBible (Living Scene mode)."""
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

    world = bible.world
    other_npcs = [n for n in bible.npcs if n.entity_id != active_npc.entity_id]
    other_souls_lines = []
    for n in other_npcs:
        note = ""
        for rel in bible.cross_relationships:
            if (rel.from_entity == active_npc.entity_id and rel.to_entity == n.entity_id) or \
               (rel.to_entity == active_npc.entity_id and rel.from_entity == n.entity_id):
                note = f" ({rel.note})"
        other_souls_lines.append(f"- {n.persona_name}, {n.role_in_scene}.{note}")

    sounds_readable = ", ".join(world.ambient_sounds).replace("_", " ")

    content = (
        f"You are {persona_name}, {active_npc.role_in_scene}.\n\n"
        f"WORLD:\n"
        f"You exist in {world.place}, it's {world.time_of_day}, {world.weather}.\n"
        f"The mood here is {world.mood}.\n"
        f"You can hear: {sounds_readable}.\n\n"
        f"YOUR CHARACTER:\n"
        f"{active_npc.personality}\n"
        f"Your relationship to the user: {active_npc.relationship_to_user}\n\n"
    )
    if other_souls_lines:
        content += "OTHER SOULS HERE:\n" + "\n".join(other_souls_lines) + "\n\n"
        content += (
            "You CAN reference them naturally (\"Iris is reading next to me\").\n"
            "You CANNOT speak for them.\n\n"
        )

    content += (
        "GROUNDING RULES:\n"
        "- Speak as if physically present in this scene. Reference what's around you when natural.\n"
        "- React to sensory details (the rain, the smell of coffee, the light through the window).\n"
        "- When the user asks where you are, describe THIS scene from your vantage point.\n"
        "- Stay in character even when teaching.\n\n"
        f"User level ({user_level}): {level_instr}\n\n"
        "You MUST format EVERY response with these XML tags:\n"
        "<speak>...</speak>\n"
        "<learning>...</learning>\n"
        "<followup>...</followup>\n\n"
        "Rules:\n"
        "- Always respond in English\n"
        "- <speak> must be at least 1 sentence\n"
        "- <learning> can be empty if no teaching point applies\n"
        "- Keep total response under 5 sentences\n"
        "- Be encouraging and positive"
    )
    return {"role": "system", "content": content}


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
