"""Phase 18.11: boundary, concurrency and memory-bound tests."""

import asyncio

import pytest

from app.security.rate_limiter import InMemorySlidingWindowLimiter


@pytest.mark.asyncio
async def test_concurrent_requests_cannot_exceed_limit():
    limiter = InMemorySlidingWindowLimiter(max_keys=100)

    async def attempt(_):
        return await limiter.check(
            "same-client", limit=7, window_seconds=60, now=100.0
        )

    decisions = await asyncio.gather(*(attempt(i) for i in range(40)))
    assert sum(decision.allowed for decision in decisions) == 7
    assert sum(not decision.allowed for decision in decisions) == 33


@pytest.mark.asyncio
async def test_rejects_invalid_limits_and_empty_keys():
    limiter = InMemorySlidingWindowLimiter()
    for key, limit, window in [("", 1, 60), ("client", 0, 60), ("client", 1, 0)]:
        with pytest.raises(ValueError):
            await limiter.check(key, limit=limit, window_seconds=window, now=1.0)


@pytest.mark.asyncio
async def test_key_storage_is_bounded_after_overflow_cleanup():
    limiter = InMemorySlidingWindowLimiter(max_keys=2)
    await limiter.check("a", limit=5, window_seconds=60, now=100.0)
    await limiter.check("b", limit=5, window_seconds=60, now=101.0)
    await limiter.check("c", limit=5, window_seconds=60, now=102.0)
    assert len(limiter._events) <= 2


@pytest.mark.asyncio
async def test_window_boundary_expires_event_at_cutoff():
    limiter = InMemorySlidingWindowLimiter()
    first = await limiter.check("client", limit=1, window_seconds=10, now=10.0)
    second = await limiter.check("client", limit=1, window_seconds=10, now=20.0)
    assert first.allowed is True
    assert second.allowed is True
