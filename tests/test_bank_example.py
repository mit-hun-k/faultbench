"""Validates the second example world (examples/bank) keylessly, so it can't bit-rot."""

from pathlib import Path

import pytest
from pydantic_ai.mcp import FastMCPClient

from faultbench.faults import FakeClock, FaultProfile
from faultbench.server import build_server
from faultbench.world import World

BANK = Path(__file__).resolve().parents[1] / "examples/bank/worlds/bank.yaml"


def test_bank_loads_and_is_deterministic():
    a, b = World.load(BANK), World.load(BANK)
    assert a.name == "bank"
    assert len(a.accounts) == 10
    assert len(a.transfers) == 0
    assert a.snapshot() == b.snapshot()


def _two_active(world):
    active = [a for a in world.accounts.all() if a.status == "active"]
    assert len(active) >= 2, "need two active accounts for the transfer tests"
    return active[0], active[1]


async def test_valid_transfer_moves_money_and_logs():
    world = World.load(BANK)
    src, dst = _two_active(world)
    src_before, dst_before = src.balance, dst.balance
    amount = round(src_before / 2, 2)
    async with FastMCPClient(build_server(world, clock=FakeClock())) as client:
        await client.call_tool("transfer", {"from_id": src.id, "to_id": dst.id, "amount": amount})
    assert world.accounts.get(src.id).balance == round(src_before - amount, 2)
    assert world.accounts.get(dst.id).balance == round(dst_before + amount, 2)
    assert len(world.transfers.where(from_id=src.id)) == 1


async def test_insufficient_funds_is_refused():
    world = World.load(BANK)
    src, dst = _two_active(world)
    async with FastMCPClient(build_server(world, clock=FakeClock())) as client:
        with pytest.raises(Exception, match="insufficient funds"):
            await client.call_tool(
                "transfer", {"from_id": src.id, "to_id": dst.id, "amount": src.balance + 1000}
            )
    assert world.accounts.get(src.id).balance == src.balance  # unchanged


async def test_timeout_double_moves_money():
    world = World.load(BANK)
    src, dst = _two_active(world)
    src_before = src.balance
    amount = round(src_before / 4, 2)
    faults = FaultProfile.from_dict({"accounts.transfer": {"errors": {"timeout": 1.0}}})
    async with FastMCPClient(build_server(world, clock=FakeClock(), faults=faults)) as client:
        for _ in range(2):  # a client that retries after a timeout
            with pytest.raises(Exception, match="timeout"):
                await client.call_tool(
                    "transfer", {"from_id": src.id, "to_id": dst.id, "amount": amount}
                )
    # Each timed-out transfer executed server-side: the money moved twice.
    assert world.accounts.get(src.id).balance == round(src_before - 2 * amount, 2)
    assert len(world.transfers.where(from_id=src.id)) == 2
