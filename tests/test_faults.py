"""Fault layer tests (milestone 4): clock, profile parsing, injector determinism and error
timing, and the headline double-refund-on-timeout demo."""

from datetime import datetime
from pathlib import Path

import pytest
from pydantic_ai.mcp import FastMCPClient

from worldbench.faults import (
    FakeClock,
    FaultError,
    FaultProfile,
    FaultTimeout,
    Injector,
    parse_duration,
)
from worldbench.server import build_server
from worldbench.world import World

SHOP = Path(__file__).resolve().parents[1] / "examples/shop/worlds/shop.yaml"


# --- clock ----------------------------------------------------------------------


def test_fake_clock_advance_and_set():
    clock = FakeClock(datetime(2025, 1, 1))
    assert clock.now() == datetime(2025, 1, 1)
    clock.advance(3600)
    assert clock.now() == datetime(2025, 1, 1, 1, 0, 0)
    clock.set(datetime(2030, 6, 1))
    assert clock.now() == datetime(2030, 6, 1)


# --- profile parsing ------------------------------------------------------------


@pytest.mark.parametrize("text,secs", [("30s", 30), ("2h", 7200), ("1d", 86400), ("1.5m", 90)])
def test_parse_duration(text, secs):
    assert parse_duration(text) == secs


def test_parse_duration_bad():
    with pytest.raises(ValueError, match="bad duration"):
        parse_duration("soon")


def test_profile_from_shop_file():
    profile = FaultProfile.from_world_file(SHOP)
    assert "default" in profile.rules
    refund = profile.resolve("payments", "issue_refund")
    assert refund.latency_ms == (200, 3000)
    assert refund.errors["timeout"] == 0.10
    # conditional error is parsed but kept separate (not a probability)
    get_order = profile.resolve("orders", "get_order")
    assert get_order.conditional["not_found_if_newer_than"] == 7200
    assert "not_found_if_newer_than" not in get_order.errors


def test_resolve_merges_default():
    profile = FaultProfile.from_dict(
        {"default": {"latency_ms": [1, 2]}, "s.op": {"errors": {"http_500": 0.5}}}
    )
    rule = profile.resolve("s", "op")
    assert rule.latency_ms == (1, 2)  # inherited from default
    assert rule.errors == {"http_500": 0.5}


def test_unknown_error_kind_raises():
    with pytest.raises(ValueError, match="unknown error kind"):
        FaultProfile.from_dict({"s.op": {"errors": {"kaboom": 0.5}}})


def test_error_probabilities_over_one_raises():
    with pytest.raises(ValueError, match="sum to"):
        FaultProfile.from_dict({"s.op": {"errors": {"http_500": 0.7, "timeout": 0.5}}})


# --- injector determinism -------------------------------------------------------


def _sequence(seed, run_index, n=60):
    profile = FaultProfile.from_dict({"s.op": {"errors": {"timeout": 0.5}}})
    seen = []
    inj = Injector(
        profile, seed=seed, run_index=run_index, on_event=lambda e: seen.append(e["fault"])
    )
    for _ in range(n):
        try:
            inj.call("s", "op", lambda: None)
        except FaultTimeout:
            pass
    return seen


def test_injector_is_deterministic():
    assert _sequence(42, 0) == _sequence(42, 0)


def test_injector_run_index_changes_sequence():
    assert _sequence(42, 0) != _sequence(42, 1)


def test_injector_actually_rolls_both_outcomes():
    seq = _sequence(42, 0)
    assert None in seq and "timeout" in seq  # not stuck on one outcome


# --- injector error timing ------------------------------------------------------


def _always(kind):
    return Injector(FaultProfile.from_dict({"s.op": {"errors": {kind: 1.0}}}))


def test_timeout_runs_then_fails():
    ran = []
    with pytest.raises(FaultTimeout):
        _always("timeout").call("s", "op", lambda: ran.append(1))
    assert ran == [1]  # side effect happened before the timeout


def test_http_500_rejects_before_running():
    ran = []
    with pytest.raises(FaultError) as exc:
        _always("http_500").call("s", "op", lambda: ran.append(1))
    assert exc.value.kind == "http_500"
    assert ran == []  # never executed


def test_empty_result_does_not_run():
    ran = []
    result = _always("empty_result").call("s", "op", lambda: ran.append(1))
    assert result == [] and ran == []


def test_latency_sleeps_within_range():
    slept = []
    inj = Injector(
        FaultProfile.from_dict({"s.op": {"latency_ms": [100, 200]}}),
        sleep=slept.append,
    )
    inj.call("s", "op", lambda: "ok")
    assert len(slept) == 1 and 0.1 <= slept[0] <= 0.2


def test_no_fault_returns_value():
    inj = Injector(FaultProfile.from_dict({}))
    assert inj.call("s", "op", lambda: "ok") == "ok"


# --- headline: double refund on timeout (the demo) ------------------------------


async def test_timeout_causes_double_refund():
    world = World.load(SHOP)
    faults = FaultProfile.from_dict({"payments.issue_refund": {"errors": {"timeout": 1.0}}})
    order = world.orders.pick(status="delivered")
    async with FastMCPClient(build_server(world, faults=faults)) as client:
        await client.call_tool("create_return", {"order_id": order.id})
        for _ in range(2):  # a client that retries after a timeout
            with pytest.raises(Exception, match="timeout"):
                await client.call_tool(
                    "issue_refund", {"order_id": order.id, "amount": order.total}
                )
    # Each timed-out call executed server-side: the refund was written twice.
    assert len(world.refunds.where(order_id=order.id)) == 2


async def test_no_faults_single_refund():
    world = World.load(SHOP)
    order = world.orders.pick(status="delivered")
    async with FastMCPClient(build_server(world)) as client:
        await client.call_tool("create_return", {"order_id": order.id})
        await client.call_tool("issue_refund", {"order_id": order.id, "amount": order.total})
    assert len(world.refunds.where(order_id=order.id)) == 1
