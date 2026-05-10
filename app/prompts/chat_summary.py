"""Prompt template for conversation summary generation."""
from __future__ import annotations


def build_summary_messages(
    conversation_text: str,
    user_level: str = "beginner",
) -> list[dict]:
    """Build messages for conversation summary extraction.

    Returns OpenAI-format chat messages asking the LLM to extract
    learning insights as JSON.
    """
    system = (
        "You are an English teacher analyzing a conversation. "
        "Extract learning insights from the conversation below.\n\n"
        "Output strict JSON with these keys:\n"
        "- new_words: list of new vocabulary words encountered\n"
        "- grammar_points: list of grammar points observed or taught\n"
        "- fluency_score: integer 1-10 estimating user fluency\n"
        "- strengths: list of positive observations\n"
        "- areas_to_improve: list of suggested improvements"
    )
    user = f"Conversation:\n{conversation_text}\n\nUser level: {user_level}"
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
