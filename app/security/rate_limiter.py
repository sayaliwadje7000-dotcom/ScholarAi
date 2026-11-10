"""Bounded, process-local sliding-window rate limiter.

This protects a single application process. Multi-worker or multi-instance
production deployments must also enforce limits at a shared gateway or use a
shared Redis-backed limiter; process-local counters are not globally shared.
"""

from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import dataclass
from time import monotonic


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    limit: int
    remaining: int
    retry_after: int
    reset_after: int


class InMemorySlidingWindowLimiter:
    def __init__(self, *, max_keys: int = 50_000):
        if max_keys <= 0:
            raise ValueError("max_keys must be positive.")
        self._max_keys = max_keys
        self._events: dict[str, deque[float]] = {}
        self._lock = asyncio.Lock()
        self._last_cleanup = monotonic()

    async def check(
        self,
        key: str,
        *,
        limit: int,
        window_seconds: int,
        now: float | None = None,
    ) -> RateLimitDecision:
        if not key or limit <= 0 or window_seconds <= 0:
            raise ValueError("A key, positive limit and positive window are required.")

        current = monotonic() if now is None else now
        cutoff = current - window_seconds

        async with self._lock:
            events = self._events.setdefault(key, deque())
            while events and events[0] <= cutoff:
                events.popleft()

            if len(events) >= limit:
                retry_after = max(1, int(events[0] + window_seconds - current + 0.999))
                decision = RateLimitDecision(
                    allowed=False,
                    limit=limit,
                    remaining=0,
                    retry_after=retry_after,
                    reset_after=retry_after,
                )
            else:
                events.append(current)
                reset_after = max(1, int(events[0] + window_seconds - current + 0.999))
                decision = RateLimitDecision(
                    allowed=True,
                    limit=limit,
                    remaining=max(0, limit - len(events)),
                    retry_after=0,
                    reset_after=reset_after,
                )

            if (
                len(self._events) > self._max_keys
                or current - self._last_cleanup >= 60
            ):
                self._prune(cutoff=current - window_seconds)
                self._last_cleanup = current

            return decision

    def _prune(self, *, cutoff: float) -> None:
        expired_keys = []
        for key, events in self._events.items():
            while events and events[0] <= cutoff:
                events.popleft()
            if not events:
                expired_keys.append(key)
        for key in expired_keys:
            self._events.pop(key, None)

        # If a burst creates more keys than the configured bound, discard the
        # oldest buckets. This is defensive memory bounding, not an identity policy.
        overflow = len(self._events) - self._max_keys
        if overflow > 0:
            oldest = sorted(
                self._events,
                key=lambda item: self._events[item][0] if self._events[item] else float("inf"),
            )[:overflow]
            for key in oldest:
                self._events.pop(key, None)
