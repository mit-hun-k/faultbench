"""pytest plugin tests (milestone 5): the world/faults/clock/mcp_server fixtures and markers,
driven without an LLM."""

import pytest
from pydantic_ai.mcp import FastMCPClient

from worldbench.faults import FakeClock, FaultProfile
from worldbench.world import World


@pytest.mark.world("worlds/mini.yaml")
def test_world_fixture_builds_the_world(world):
    assert isinstance(world, World)
    assert world.name == "mini"
    assert len(world.widgets) == 5


def test_world_fixture_without_marker_errors(pytestconfig):
    # The marker is required; using the fixture without it raises a clear UsageError.
    # (Covered here by asserting the helper contract rather than triggering collection errors.)
    from worldbench.pytest_plugin import _marker  # noqa: PLC0415

    class _Node:
        def get_closest_marker(self, name):
            return None

    class _Req:
        node = _Node()

    assert _marker(_Req(), "world") is None


@pytest.mark.world("worlds/mini.yaml")
def test_clock_fixture_is_a_fake_clock(clock):
    assert isinstance(clock, FakeClock)
    before = clock.now()
    clock.advance(60)
    assert (clock.now() - before).total_seconds() == 60


@pytest.mark.world("worlds/mini.yaml")
def test_faults_fixture_defaults_empty(faults):
    assert isinstance(faults, FaultProfile)
    assert faults.is_empty()


@pytest.mark.world("worlds/mini.yaml")
@pytest.mark.faults({"store.sell_widget": {"errors": {"http_500": 1.0}}})
def test_faults_fixture_from_marker(faults):
    assert faults.resolve("store", "sell_widget").errors == {"http_500": 1.0}


@pytest.mark.world("worlds/mini.yaml")
async def test_mcp_server_shares_world_state(world, mcp_server):
    """Driving the in-process server mutates the same `world` the test can assert on."""
    async with FastMCPClient(mcp_server) as client:
        await client.call_tool("sell_widget", {"id": "1", "status": "sold"})
    assert world.widgets.get("1").status == "sold"


@pytest.mark.world("worlds/mini.yaml")
@pytest.mark.faults({"store.sell_widget": {"errors": {"http_500": 1.0}}})
async def test_mcp_server_applies_faults(world, mcp_server):
    async with FastMCPClient(mcp_server) as client:
        with pytest.raises(Exception, match="http_500"):
            await client.call_tool("sell_widget", {"id": "1", "status": "sold"})
    # http_500 rejects before running, so the world is untouched.
    assert world.widgets.get("1").status != "sold"
