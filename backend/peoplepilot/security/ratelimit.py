"""Small in-process sliding-window rate limiter (per key).

Good enough for a single-process self-hosted install. For multiple replicas, back it
with Redis or Postgres instead.
"""
from __future__ import annotations

import threading
import time
from collections import defaultdict, deque


class RateLimiter:
    def __init__(self, limit: int, window_seconds: float) -> None:
        self.limit = limit
        self.window = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            q = self._hits[key]
            while q and now - q[0] > self.window:
                q.popleft()
            if len(q) >= self.limit:
                return False
            q.append(now)
            return True

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


admin_login_limiter = RateLimiter(limit=10, window_seconds=300)
portal_code_limiter = RateLimiter(limit=5, window_seconds=600)
webhook_limiter = RateLimiter(limit=120, window_seconds=60)
