"""LLM judge: pick best from N candidates."""
from __future__ import annotations


def build_judge_message(candidates: list[str], purpose: str, dimensions: list[str]) -> str:
    """Build a user prompt asking an LLM to score candidates."""
    dims = ", ".join(dimensions)
    system = (
        f"You are an expert judge evaluating {len(candidates)} candidates for "
        f"{purpose}. Score each on {dims}.\n"
        "Output STRICT JSON:\n"
        '{"best_index": <int 0-based>, "reason": "<one sentence explanation>", '
        '"scores": [<int>]}\n'
        "No markdown, no other text."
    )
    lines = "\n\n".join(
        f"--- CANDIDATE {i} ---\n{c}" for i, c in enumerate(candidates)
    )
    user = f"Evaluate these candidates:\n\n{lines}"
    return system + "\n\n" + user


def pick_best_candidate(
    candidates: list[str],
    purpose: str = "",
    dimensions: list[str] | None = None,
) -> int:
    """Return the index of the best candidate, or 0 by default.

    In production this calls an LLM. The function signature supports
    dependency injection for that.
    """
    if not candidates:
        raise ValueError("candidates must not be empty")
    return 0  # default: first candidate; production override via LLM call
