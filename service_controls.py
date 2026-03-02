"""Security and traffic control primitives for backend service."""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque


def is_api_key_valid(expected_key: str, provided_key: str | None) -> bool:
    """Validate API key when expected key is configured."""
    if not expected_key:
        return True
    return provided_key == expected_key


class SlidingWindowRateLimiter:
    """Per-client in-memory sliding window rate limiter."""

    def __init__(self, max_requests: int, window_seconds: int) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, client_id: str) -> bool:
        """Return True when client request should be allowed."""
        now = time.time()
        window_start = now - self.window_seconds

        with self._lock:
            timestamps = self._requests[client_id]
            while timestamps and timestamps[0] < window_start:
                timestamps.popleft()

            if len(timestamps) >= self.max_requests:
                return False

            timestamps.append(now)
            return True
