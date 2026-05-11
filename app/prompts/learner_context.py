"""Prompt template for learner context injection.

The chat orchestrator prepends a learner-context system message so the persona
can recycle vocab the learner has actually been seeing and stay calibrated to
their level. The message is intentionally short — it competes with the persona
system prompt for the model's attention budget.
"""
from __future__ import annotations


def build_learner_context_message(
    level: str | None,
    recent_vocab: list[str] | None = None,
    weak_areas: list[str] | None = None,
) -> dict | None:
    """Return a system-role learner-context message, or None when empty.

    Returns None when there is nothing useful to say — keeps the LLM context
    clean for first-time users who have no history yet.
    """
    parts: list[str] = []

    normalized_level = (level or "").strip()
    if normalized_level:
        parts.append(f"The learner is at the {normalized_level} level.")

    vocab = [w for w in (recent_vocab or []) if w.strip()]
    if vocab:
        capped = vocab[:20]
        parts.append(
            "Recently learned vocabulary: "
            + ", ".join(capped)
            + ". Recycle these words when natural; avoid words the learner has not seen."
        )

    areas = [a for a in (weak_areas or []) if a.strip()]
    if areas:
        parts.append("Areas they're working on: " + "; ".join(areas) + ".")

    if not parts:
        return None

    return {"role": "system", "content": " ".join(parts)}
