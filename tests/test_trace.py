"""Trace recorder + queries, and recorder wiring into the server (milestone 6). Keyless."""

import json
from pathlib import Path

import pytest
from pydantic_ai.mcp import FastMCPClient

from faultbench.faults import FaultProfile
from faultbench.server import build_server
from faultbench.trace import Recorder, Trace
from faultbench.world import World

SHOP = Path(__file__).resolve().parents[1] / "examples/shop/worlds/shop.yaml"


def test_recorder_event_shape(tmp_path):
    rec = Recorder(run=3, path=tmp_path / "t.jsonl")
    rec.record(
        tool="get_order",
        args={"id": "1"},
        ok=True,
        world_rev=0,
        latency_ms=12.5,
        result={"id": "1"},
    )
    rec.record(
        tool="issue_refund",
        args={"order_id": "1"},
        ok=False,
        world_rev=1,
        fault="timeout",
        error="boom",
    )
    e0, e1 = rec.events
    assert e0["run"] == 3 and e0["seq"] == 0 and e0["ok"] and e0["result"] == {"id": "1"}
    assert e0["latency_ms"] == 12.5 and e0["fault"] is None
    assert e1["seq"] == 1 and e1["fault"] == "timeout" and e1["error"] == "boom"
    assert "result" not in e1
    lines = (tmp_path / "t.jsonl").read_text().splitlines()
    assert len(lines) == 2 and json.loads(lines[1])["fault"] == "timeout"


def test_trace_queries():
    events = [
        {"tool": "a", "ok": True, "fault": None},
        {"tool": "a", "ok": False, "fault": "timeout"},
        {"tool": "b", "ok": True, "fault": None},
    ]
    t = Trace(events)
    assert t.count("a") == 2
    assert len(t.calls_to("a")) == 2
    assert len(t.faults()) == 1
    assert len(t.failures()) == 1
    assert len(t) == 3
    assert t.summary() == "a → a!timeout → b"


def test_trace_from_file(tmp_path):
    p = tmp_path / "t.jsonl"
    rec = Recorder(path=p)
    rec.record(tool="x", args={}, ok=True, world_rev=0)
    assert Trace.from_file(p).count("x") == 1


async def test_recorder_wired_into_server():
    world = World.load(SHOP)
    faults = FaultProfile.from_dict({"payments.issue_refund": {"errors": {"timeout": 1.0}}})
    rec = Recorder()
    order = world.orders.pick(status="delivered")
    async with FastMCPClient(build_server(world, faults=faults, recorder=rec)) as client:
        await client.call_tool("get_order", {"id": order.id})
        with pytest.raises(Exception, match="timeout"):
            await client.call_tool("issue_refund", {"order_id": order.id, "amount": order.total})
    t = Trace(rec.events)
    assert t.count("get_order") == 1
    refund_call = t.calls_to("issue_refund")[0]
    assert refund_call["fault"] == "timeout"
    assert refund_call["ok"] is False
    assert len(t.faults()) == 1 and len(t.failures()) == 1
