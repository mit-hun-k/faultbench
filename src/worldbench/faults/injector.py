"""Fault injector: wraps an operation call and applies latency + errors. Milestone 4.

Determinism: all randomness comes from `Random(f"{seed}:{run_index}")`, so the same profile,
seed, and run index produce the same fault sequence across processes.

Error timing models real failures:
  - `timeout`: the request reached the server and RAN (its side effect happened), but the
    client gave up waiting. So the op executes, then a FaultTimeout is raised. A client that
    retries will run it again — this is how a timeout becomes a double write.
  - `http_500` / `http_429` / `not_found`: the request is rejected BEFORE running, so there
    is no side effect.
  - `empty_result` / `malformed_json`: the response is corrupted; the op does NOT run.
"""

from __future__ import annotations

import random
import sys
import time
from collections.abc import Callable
from typing import Any

from .profile import FaultProfile, FaultRule

# error kinds that reject the call before the operation runs (no side effect)
_REJECT_BEFORE = frozenset({"http_500", "http_429", "not_found"})
# error kinds that corrupt the response without running the operation
_CORRUPT_RESPONSE = frozenset({"empty_result", "malformed_json"})


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

    def call(self, service: str, op: str, fn: Callable[[], Any]) -> Any:
        """Run `fn` under the fault rule for `service.op`."""
        rule = self.profile.resolve(service, op)
        self._apply_latency(rule)
        kind = self._roll(rule.errors)
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
    def _apply_latency(self, rule: FaultRule) -> None:
        if rule.latency_ms:
            lo, hi = rule.latency_ms
            self._sleep(self._rng.uniform(lo, hi) / 1000.0)

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
            print(f"[worldbench:fault] {service}.{op} -> {kind}", file=sys.stderr)
        if self._on_event:
            self._on_event(event)
