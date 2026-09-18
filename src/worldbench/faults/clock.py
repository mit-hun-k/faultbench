"""FakeClock: the only source of time inside a world. Milestone 4.

The engine, handlers, and injector read "now" only from a FakeClock, so time-dependent
behaviour ("this order is 2 hours old") is testable without waiting. A FakeClock never
advances on its own — a test moves it with `advance()` or `set()`.
"""

from __future__ import annotations

from datetime import datetime, timedelta

# A fixed default "now", so a clock with no explicit start is still deterministic.
DEFAULT_NOW = datetime(2025, 6, 1)


class FakeClock:
    def __init__(self, now: datetime | None = None) -> None:
        self._now = now or DEFAULT_NOW

    def now(self) -> datetime:
        return self._now

    def advance(self, seconds: float) -> datetime:
        self._now += timedelta(seconds=seconds)
        return self._now

    def set(self, when: datetime) -> datetime:
        self._now = when
        return self._now

    def __repr__(self) -> str:
        return f"FakeClock({self._now.isoformat()})"
