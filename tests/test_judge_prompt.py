from __future__ import annotations

from app.prompts.judge import build_judge_message, pick_best_candidate


def test_build_judge_message_includes_candidates():
    candidates = ["bible A content", "bible B content"]
    msg = build_judge_message(candidates, "scene bible", ["coherence", "character depth"])
    assert "bible A" in msg
    assert "coherence" in msg


def test_pick_best_candidate_no_error():
    candidates = ["alpha", "beta"]
    result = pick_best_candidate(candidates, "test", ["x"])
    assert result == 0  # first as default
