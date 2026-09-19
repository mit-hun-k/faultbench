"""Rules & smarter faults (milestone 7): clock/seed alignment, conditional not-found
(sync lag), the return-window eligibility rule, and rate limits. Keyless."""

from datetime import datetime, timedelta
from pathlib import Path

import pytest
from pydantic_ai.mcp import FastMCPClient

from worldbench.faults import FakeClock, FaultError, FaultProfile, Injector
from worldbench.faults.clock import DEFAULT_NOW
from worldbench.server import build_server
from worldbench.world import World
from worldbench.world.seed import WORLD_EPOCH

SHOP = Path(__file__).resolve().parents[1] / "examples/shop/worlds/shop.yaml"
MINI = Path(__file__).parent / "worlds/mini.yaml"


def test_clock_matches_seed_epoch():
    # Drift guard: the seed window ends where the default clock 'now' is, so seeded records
    # are recent and time-dependent rules have eligible data.
    assert DEFAULT_NOW == WORLD_EPOCH


def test_seed_dates_are_within_window_of_epoch():
    world = World.load(SHOP)
    for o in world.orders.all():
        age = (WORLD_EPOCH - datetime.fromisoformat(o.placed_at)).days
        assert 0 <= age <= 20


# --- conditional not-found (sync lag), injector level ----------------------------


def test_injector_not_found_when_record_is_recent():
    prof = FaultProfile.from_dict(
        {"orders.get_order": {"errors": {"not_found_if_newer_than": "2h"}}}
    )
    clock = FakeClock(datetime(2025, 6, 1, 12))
    inj = Injector(prof, clock=clock)
    ran = []
    with pytest.raises(FaultError) as exc:
        inj.call("orders", "get_order", lambda: ran.append(1), record_time=datetime(2025, 6, 1, 11))
    assert exc.value.kind == "not_found"
    assert ran == []  # a record within the window is invisible; op never runs


def test_injector_visible_when_record_is_old_enough():
    prof = FaultProfile.from_dict(
        {"orders.get_order": {"errors": {"not_found_if_newer_than": "2h"}}}
    )
    clock = FakeClock(datetime(2025, 6, 1, 12))
    inj = Injector(prof, clock=clock)
    # placed 3h ago (> 2h) -> visible
    assert (
        inj.call("orders", "get_order", lambda: "ok", record_time=datetime(2025, 6, 1, 9)) == "ok"
    )


# --- rate limit, injector level -------------------------------------------------


def test_injector_rate_limit():
    prof = FaultProfile.from_dict({"s.op": {"rate_limit": {"calls": 2, "per_seconds": 60}}})
    clock = FakeClock(datetime(2025, 1, 1))
    inj = Injector(prof, clock=clock)
    assert inj.call("s", "op", lambda: "ok") == "ok"
    assert inj.call("s", "op", lambda: "ok") == "ok"
    with pytest.raises(FaultError) as exc:
        inj.call("s", "op", lambda: "ok")
    assert exc.value.kind == "http_429"
    clock.advance(61)  # window rolls forward
    assert inj.call("s", "op", lambda: "ok") == "ok"


# --- eligibility (return window), through the server -----------------------------


async def test_return_window_eligibility():
    world = World.load(SHOP)
    clock = FakeClock()  # default now == seed epoch, so delivered orders are recent
    async with FastMCPClient(build_server(world, clock=clock)) as client:
        recent = world.orders.pick(status="delivered")
        await client.call_tool("create_return", {"order_id": recent.id})
        assert world.orders.get(recent.id).status == "returned"

        clock.set(WORLD_EPOCH + timedelta(days=60))  # now every order is far past 30 days
        old = world.orders.pick(status="delivered")
        with pytest.raises(Exception, match="window"):
            await client.call_tool("create_return", {"order_id": old.id})
        assert world.orders.get(old.id).status == "delivered"  # unchanged


# --- sync lag, through the server -----------------------------------------------


async def test_sync_lag_not_found_then_visible():
    world = World.load(SHOP)
    clock = FakeClock()
    faults = FaultProfile.from_dict(
        {"orders.get_order": {"errors": {"not_found_if_newer_than": "2h"}}}
    )
    order = world.orders.all()[0]
    placed = datetime.fromisoformat(order.placed_at)
    async with FastMCPClient(build_server(world, clock=clock, faults=faults)) as client:
        clock.set(placed + timedelta(hours=1))  # 1h old: not yet visible
        with pytest.raises(Exception, match="not_found"):
            await client.call_tool("get_order", {"id": order.id})
        clock.set(placed + timedelta(hours=3))  # 3h old: visible
        assert (await client.call_tool("get_order", {"id": order.id})).content


# --- rate limit, through the server ---------------------------------------------


async def test_rate_limit_through_server():
    world = World.load(MINI)
    clock = FakeClock()
    faults = FaultProfile.from_dict(
        {"store.sell_widget": {"rate_limit": {"calls": 2, "per_seconds": 60}}}
    )
    async with FastMCPClient(build_server(world, clock=clock, faults=faults)) as client:
        await client.call_tool("sell_widget", {"id": "1", "status": "sold"})
        await client.call_tool("sell_widget", {"id": "2", "status": "sold"})
        with pytest.raises(Exception, match="http_429"):
            await client.call_tool("sell_widget", {"id": "3", "status": "sold"})
        clock.advance(61)
        await client.call_tool("sell_widget", {"id": "3", "status": "sold"})  # allowed again
    assert world.widgets.get("3").status == "sold"
