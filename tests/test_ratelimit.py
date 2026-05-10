"""Tests for app.utils.ratelimit.MemoryRateLimiter."""
from __future__ import annotations


def test_allows_within_quota():
    from app.utils.ratelimit import MemoryRateLimiter

    rl = MemoryRateLimiter(max_per_window=3, window_seconds=60.0)
    now = 1000.0
    for _ in range(3):
        ok, retry_after = rl.check("ip_1", now=now)
        assert ok is True
        assert retry_after == 0


def test_blocks_when_quota_exceeded():
    from app.utils.ratelimit import MemoryRateLimiter

    rl = MemoryRateLimiter(max_per_window=3, window_seconds=60.0)
    now = 1000.0
    for _ in range(3):
        rl.check("ip_1", now=now)
    ok, retry_after = rl.check("ip_1", now=now)
    assert ok is False
    assert 0 < retry_after <= 60


def test_quota_resets_after_window_slides():
    from app.utils.ratelimit import MemoryRateLimiter

    rl = MemoryRateLimiter(max_per_window=2, window_seconds=10.0)
    rl.check("ip_1", now=100.0)
    rl.check("ip_1", now=101.0)
    blocked, _ = rl.check("ip_1", now=105.0)
    assert blocked is False

    # 11 秒后,前两次落出窗口,应该再放行
    ok, _ = rl.check("ip_1", now=112.0)
    assert ok is True


def test_separate_keys_have_independent_quotas():
    from app.utils.ratelimit import MemoryRateLimiter

    rl = MemoryRateLimiter(max_per_window=1, window_seconds=60.0)
    a_ok, _ = rl.check("ip_a", now=100.0)
    b_ok, _ = rl.check("ip_b", now=100.0)
    assert a_ok is True
    assert b_ok is True

    a_blocked, _ = rl.check("ip_a", now=100.0)
    assert a_blocked is False


def test_retry_after_is_ceil_of_remaining_window():
    from app.utils.ratelimit import MemoryRateLimiter

    rl = MemoryRateLimiter(max_per_window=1, window_seconds=60.0)
    rl.check("ip_x", now=100.0)
    ok, retry_after = rl.check("ip_x", now=130.0)
    assert ok is False
    assert retry_after == 30  # 60 - (130 - 100)
