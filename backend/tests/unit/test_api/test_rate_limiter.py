"""Tests for the WebSocket per-connection sliding-window rate limiter."""

from istari.api.routes.chat import _RateLimiter


class TestRateLimiter:
    def test_allows_up_to_limit(self) -> None:
        rl = _RateLimiter(limit=5, window=60.0)
        for _ in range(5):
            assert rl.is_allowed() is True

    def test_blocks_over_limit(self) -> None:
        rl = _RateLimiter(limit=5, window=60.0)
        for _ in range(5):
            rl.is_allowed()
        assert rl.is_allowed() is False

    def test_does_not_record_blocked_attempt(self) -> None:
        """A blocked call must not consume a slot — still blocked on the next call."""
        rl = _RateLimiter(limit=3, window=60.0)
        for _ in range(3):
            rl.is_allowed()
        assert rl.is_allowed() is False
        assert rl.is_allowed() is False

    def test_window_expiry_allows_new_messages(self) -> None:
        """Timestamps older than the window are evicted, freeing up slots."""
        import unittest.mock as mock

        rl = _RateLimiter(limit=3, window=10.0)
        base = 1000.0
        # calls 1-3 at t=0 (fill), call 4 at t=0 (blocked), call 5 at t=11 (evicts all → allowed)
        times = [base, base, base, base, base + 11.0]
        idx = 0

        def fake_monotonic() -> float:
            nonlocal idx
            t = times[idx]
            idx += 1
            return t

        with mock.patch("istari.api.routes.chat.time.monotonic", fake_monotonic):
            assert rl.is_allowed() is True   # t=0, slot 1
            assert rl.is_allowed() is True   # t=0, slot 2
            assert rl.is_allowed() is True   # t=0, slot 3 (full)
            assert rl.is_allowed() is False  # t=0, over limit
            assert rl.is_allowed() is True   # t=11, all evicted → slot 1

    def test_independent_limiters_per_connection(self) -> None:
        """Each connection gets its own limiter; one hitting the limit doesn't affect another."""
        rl1 = _RateLimiter(limit=2, window=60.0)
        rl2 = _RateLimiter(limit=2, window=60.0)
        rl1.is_allowed()
        rl1.is_allowed()
        assert rl1.is_allowed() is False
        assert rl2.is_allowed() is True
