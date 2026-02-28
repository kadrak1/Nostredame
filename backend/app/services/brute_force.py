"""In-memory brute-force protection for login attempts.

Tracks failed attempts per (IP, login) pair.
After MAX_ATTEMPTS failures within the window, blocks for BLOCK_SECONDS.
"""

import time
from dataclasses import dataclass, field

MAX_ATTEMPTS = 5
BLOCK_SECONDS = 15 * 60  # 15 minutes


@dataclass
class _Record:
    attempts: int = 0
    first_attempt: float = 0.0
    blocked_until: float = 0.0


class BruteForceGuard:
    """Thread-safe brute-force guard (single-process, in-memory)."""

    def __init__(
        self,
        max_attempts: int = MAX_ATTEMPTS,
        block_seconds: int = BLOCK_SECONDS,
    ) -> None:
        self._max_attempts = max_attempts
        self._block_seconds = block_seconds
        self._records: dict[str, _Record] = {}

    def _key(self, ip: str, login: str) -> str:
        return f"{ip}:{login}"

    def is_blocked(self, ip: str, login: str) -> bool:
        """Return True if the (ip, login) pair is currently blocked."""
        rec = self._records.get(self._key(ip, login))
        if rec is None:
            return False
        if rec.blocked_until and time.monotonic() < rec.blocked_until:
            return True
        return False

    def record_failure(self, ip: str, login: str) -> None:
        """Record a failed login attempt. May trigger a block."""
        key = self._key(ip, login)
        now = time.monotonic()
        rec = self._records.get(key)

        if rec is None:
            rec = _Record(attempts=1, first_attempt=now)
            self._records[key] = rec
            return

        # If previously blocked and block expired — reset
        if rec.blocked_until and now >= rec.blocked_until:
            rec.attempts = 1
            rec.first_attempt = now
            rec.blocked_until = 0.0
            return

        rec.attempts += 1

        if rec.attempts >= self._max_attempts:
            rec.blocked_until = now + self._block_seconds

    def record_success(self, ip: str, login: str) -> None:
        """Clear failure record on successful login."""
        self._records.pop(self._key(ip, login), None)

    def remaining_block_seconds(self, ip: str, login: str) -> int:
        """Return how many seconds remain on the block (0 if not blocked)."""
        rec = self._records.get(self._key(ip, login))
        if rec is None or not rec.blocked_until:
            return 0
        remaining = rec.blocked_until - time.monotonic()
        return max(0, int(remaining))


# Singleton instance used by the auth router
login_guard = BruteForceGuard()
