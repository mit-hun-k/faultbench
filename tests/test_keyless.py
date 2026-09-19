"""The documented keyless way to exercise a world: drive the in-process server directly with
`await mcp_server.call_tool(...)` — no agent, no model key, core `mcp` dependency only. This
is how you test operations, custom rules, and faults without paying for / waiting on an LLM."""

import pytest


@pytest.mark.world("worlds/mini.yaml")
async def test_call_tool_mutates_world(world, mcp_server):
    await mcp_server.call_tool("sell_widget", {"id": "1", "status": "sold"})
    assert world.widgets.get("1").status == "sold"  # assert on the shared world directly


@pytest.mark.world("worlds/mini.yaml")
@pytest.mark.faults({"store.sell_widget": {"errors": {"timeout": 1.0}}})
async def test_fault_is_observable_in_trace(mcp_server, trace):
    with pytest.raises(Exception, match="timeout"):
        await mcp_server.call_tool("sell_widget", {"id": "1", "status": "sold"})
    assert [e["fault"] for e in trace.faults()] == ["timeout"]
