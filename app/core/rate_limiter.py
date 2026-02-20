import time
from collections import defaultdict, deque
from threading import Lock
from typing import Dict, Deque, Optional


class InMemoryRateLimiter:
    """
    Thread-safe sliding window rate limiter.

    Features:
    - Per-key sliding window
    - Configurable window size
    - O(1) cleanup using deque
    - Memory-safe pruning
    - Usage metrics support
    """

    def __init__(self, window_seconds: int = 60):
        self.window_seconds = window_seconds
        self.requests: Dict[str, Deque[float]] = defaultdict(deque)
        self.lock = Lock()

    # -----------------------------------------------------
    # Core Check
    # -----------------------------------------------------
    def is_allowed(self, key: str, limit: int) -> bool:
        """
        Returns True if request allowed, False if rate limit exceeded.
        """

        now = time.time()
        window_start = now - self.window_seconds

        with self.lock:
            queue = self.requests[key]

            # Remove expired timestamps (O(k))
            while queue and queue[0] < window_start:
                queue.popleft()

            if len(queue) >= limit:
                return False

            queue.append(now)
            return True

    # -----------------------------------------------------
    # Remaining Requests
    # -----------------------------------------------------
    def remaining(self, key: str, limit: int) -> int:
        """
        Returns remaining requests in current window.
        """

        now = time.time()
        window_start = now - self.window_seconds

        with self.lock:
            queue = self.requests[key]

            while queue and queue[0] < window_start:
                queue.popleft()

            return max(limit - len(queue), 0)

    # -----------------------------------------------------
    # Reset a Key
    # -----------------------------------------------------
    def reset(self, key: str):
        """
        Clears rate limit data for a specific key.
        Useful when rotating keys.
        """

        with self.lock:
            if key in self.requests:
                del self.requests[key]

    # -----------------------------------------------------
    # Cleanup Idle Keys
    # -----------------------------------------------------
    def cleanup(self, idle_seconds: Optional[int] = 300):
        """
        Removes keys that have been idle for a long time.
        Prevents memory bloat.
        """

        now = time.time()

        with self.lock:
            keys_to_delete = []

            for key, queue in self.requests.items():
                if not queue:
                    keys_to_delete.append(key)
                elif now - queue[-1] > idle_seconds:
                    keys_to_delete.append(key)

            for key in keys_to_delete:
                del self.requests[key]

    # -----------------------------------------------------
    # Debug / Metrics
    # -----------------------------------------------------
    def stats(self) -> Dict:
        """
        Returns internal stats for monitoring.
        """

        with self.lock:
            return {
                "total_tracked_keys": len(self.requests),
                "window_seconds": self.window_seconds
            }


# ---------------------------------------------------------
# Global Singleton Instance
# ---------------------------------------------------------
rate_limiter = InMemoryRateLimiter(window_seconds=60)