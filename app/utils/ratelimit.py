"""Single-instance in-memory sliding window rate limiter."""
from __future__ import annotations

import math
import time
from collections import deque


class MemoryRateLimiter:
    """Per-key sliding window: at most `max_per_window` events in `window_seconds`."""

    def __init__(self, *, max_per_window: int, window_seconds: float) -> None:
        if max_per_window <= 0:
            raise ValueError("max_per_window must be > 0")
        if window_seconds <= 0:
            raise ValueError("window_seconds must be > 0")
        self._max = max_per_window
        self._window = window_seconds
        self._buckets: dict[str, deque[float]] = {}

    def check(self, key: str, *, now: float | None = None) -> tuple[bool, int]:
        """Returns (allowed, retry_after_s).

        retry_after_s = 0 when allowed; otherwise ceil seconds until oldest event drops out.
        Accepted requests are recorded; rejected ones are NOT.
        """
        ts = now if now is not None else time.monotonic()
        bucket = self._buckets.setdefault(key, deque())
        cutoff = ts - self._window

        while bucket and bucket[0] <= cutoff:
            bucket.popleft()

        if len(bucket) < self._max:
            bucket.append(ts)
            return True, 0

        oldest = bucket[0]
        retry_after = math.ceil(self._window - (ts - oldest))
        return False, max(retry_after, 1)
