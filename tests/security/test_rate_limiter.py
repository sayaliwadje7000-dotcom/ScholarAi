import pytest

from app.security.rate_limiter import InMemorySlidingWindowLimiter


@pytest.mark.asyncio
async def test_allows_requests_under_limit():
    limiter = InMemorySlidingWindowLimiter()
    first = await limiter.check("client", limit=2, window_seconds=60, now=100.0)
    second = await limiter.check("client", limit=2, window_seconds=60, now=101.0)
    assert first.allowed is True
    assert first.remaining == 1
    assert second.allowed is True
    assert second.remaining == 0


@pytest.mark.asyncio
async def test_blocks_request_at_limit_and_returns_retry_after():
    limiter = InMemorySlidingWindowLimiter()
    await limiter.check("client", limit=1, window_seconds=60, now=100.0)
    blocked = await limiter.check("client", limit=1, window_seconds=60, now=105.0)
    assert blocked.allowed is False
    assert blocked.remaining == 0
    assert blocked.retry_after == 55


@pytest.mark.asyncio
async def test_sliding_window_expires_old_events():
    limiter = InMemorySlidingWindowLimiter()
    await limiter.check("client", limit=1, window_seconds=10, now=100.0)
    allowed = await limiter.check("client", limit=1, window_seconds=10, now=110.1)
    assert allowed.allowed is True


@pytest.mark.asyncio
async def test_keys_are_isolated():
    limiter = InMemorySlidingWindowLimiter()
    await limiter.check("client-a", limit=1, window_seconds=60, now=100.0)
    decision = await limiter.check("client-b", limit=1, window_seconds=60, now=100.0)
    assert decision.allowed is True
