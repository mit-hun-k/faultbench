"""Fault injector: wraps an operation call and applies latency + errors. Milestones 4, 7.

Determinism: all randomness comes from `Random(f"{seed}:{run_index}")`, so the same profile,
seed, and run index produce the same fault sequence across processes. Conditional faults and
rate limits are deterministic (data- and clock-driven, no RNG).

Order of checks per call: latency → conditional not-found → rate limit → probabilistic error.

Error timing models real failures:
  - `timeout`: the request reached the server and RAN (its side effect happened), but the
    client gave up waiting. So the op executes, then a FaultTimeout is raised. A client that
    retries will run it again — this is how a timeout becomes a double write.
  - `http_500` / `http_429` / `not_found`: the request is rejected BEFORE running, so there
    is no side effect.
  - `empty_result` / `malformed_json`: the response is corrupted; the op does NOT run.

Conditional (milestone 7):
  - `not_found_if_newer_than: 2h`: a read of a record whose timestamp is newer than 2h before
    `clock.now()` returns not_found — models sync lag (recent writes not yet visible).
  - `rate_limit: {calls, per_seconds}`: after `calls` calls within the window, returns
    http_429 until the window rolls forward (measured on the clock).
"""

from __future__ import annotations

import random
import sys
import time
from collections.abc import Callable
from datetime import datetime
from typing import Any

from .profile import FaultProfile, FaultRule


class FaultTimeout(Exception):
    """The operation ran, but the client 'timed out' before getting the result."""


class FaultError(Exception):
    """The operation was rejected by an injected fault before it ran (or its response was
    corrupted)."""

    def __init__(self, kind: str, message: str | None = None) -> None:
        self.kind = kind
        super().__init__(message or f"injected {kind}")


class Injector:
    def __init__(
        self,
        profile: FaultProfile,
        seed: int = 0,
        run_index: int = 0,
        clock: Any = None,
        sleep: Callable[[float], None] = time.sleep,
        timeout_seconds: float = 0.0,
        on_event: Callable[[dict], None] | None = None,
    ) -> None:
        self.profile = profile
        self.clock = clock
        self._rng = random.Random(f"{seed}:{run_index}")
        self._sleep = sleep
        self._timeout_seconds = timeout_seconds
        self._on_event = on_event
        self._rl_calls: dict[str, list[float]] = {}  # service.op -> recent call times (rate limit)

    def call(
        self,
        service: str,
        op: str,
        fn: Callable[[], Any],
        on_decision: Callable[[str | None, float], None] | None = None,
        record_time: datetime | None = None,
    ) -> Any:
        """Run `fn` under the fault rule for `service.op`.

        `on_decision(fault_kind, latency_ms)` is called once the fault is decided, before the
        operation runs — so a recorder can log what was injected even if the call then fails.
        `record_time` is the target record's timestamp, used by conditional not-found rules.
        """
        rule = self.profile.resolve(service, op)
        latency_ms = self._apply_latency(rule)
        kind = self._conditional(rule, record_time) or self._rate_limited(service, op, rule)
        if kind is None:
            kind = self._roll(rule.errors)
        if on_decision:
            on_decision(kind, latency_ms)
        self._emit(service, op, kind)
        if kind is None:
            return fn()
        if kind == "timeout":
            fn()  # side effect happens; the result is lost because the client "times out"
            if self._timeout_seconds:
                self._sleep(self._timeout_seconds)
            raise FaultTimeout(f"{op} timed out after executing")
        if kind == "empty_result":
            return []
        if kind == "malformed_json":
            return "}{ not valid json"
        raise FaultError(kind, f"{op}: injected {kind}")

    # --- internals ---------------------------------------------------------------
    def _conditional(self, rule: FaultRule, record_time: datetime | None) -> str | None:
        """Return 'not_found' when the record is newer than the sync-lag window."""
        window = rule.conditional.get("not_found_if_newer_than")
        if window is None or record_time is None or self.clock is None:
            return None
        age = (self.clock.now() - record_time).total_seconds()
        return "not_found" if age < window else None

    def _rate_limited(self, service: str, op: str, rule: FaultRule) -> str | None:
        """Return 'http_429' once more than `calls` calls happen within the window."""
        limit = rule.rate_limit
        if limit is None:
            return None
        now = self.clock.now().timestamp() if self.clock is not None else time.monotonic()
        key = f"{service}.{op}"
        recent = [t for t in self._rl_calls.get(key, []) if now - t < limit.per_seconds]
        if len(recent) >= limit.calls:
            self._rl_calls[key] = recent
            return "http_429"
        recent.append(now)
        self._rl_calls[key] = recent
        return None

    def _apply_latency(self, rule: FaultRule) -> float:
        if not rule.latency_ms:
            return 0.0
        lo, hi = rule.latency_ms
        ms = self._rng.uniform(lo, hi)
        self._sleep(ms / 1000.0)
        return ms

    def _roll(self, errors: dict[str, float]) -> str | None:
        if not errors:
            return None
        r = self._rng.random()
        cumulative = 0.0
        for kind, prob in errors.items():  # insertion order (from YAML) => deterministic
            cumulative += prob
            if r < cumulative:
                return kind
        return None

    def _emit(self, service: str, op: str, kind: str | None) -> None:
        event = {"service": service, "op": op, "fault": kind}
        if kind:
            print(f"[faultbench:fault] {service}.{op} -> {kind}", file=sys.stderr)
        if self._on_event:
            self._on_event(event)
