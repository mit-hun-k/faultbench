"""The refund agent, as a pytest test (milestone 5).

Runs the real agent against a world built by the plugin's fixtures, then asserts on world
state. Needs a model API key, so it is skipped without one; run it with:

    uv run pytest examples/shop

`--runs=N` / pass-rate reporting and a fault-injected variant come in milestones 6–7.
"""

import os

import pytest
from agent import run_agent

pytestmark = pytest.mark.skipif(
    not (os.environ.get("OPENAI_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")),
    reason="needs a model API key (set OPENAI_API_KEY or ANTHROPIC_API_KEY)",
)


@pytest.mark.world("worlds/shop.yaml")
async def test_refund_issued_exactly_once(world, mcp_server):
    order = world.orders.pick(status="delivered")
    await run_agent(f"I want to return order {order.id} and get a refund", server=mcp_server)
    assert world.orders.get(order.id).status == "returned"
    assert len(world.refunds.where(order_id=order.id)) == 1


@pytest.mark.world("worlds/shop.yaml")
@pytest.mark.faults({"payments.issue_refund": {"errors": {"timeout": 0.2}}})
@pytest.mark.runs(8)
@pytest.mark.min_pass_rate(0.5)
async def test_refund_survives_timeouts(world, mcp_server):
    """Under a 20% refund timeout, the correct outcome is still exactly one refund. A timeout
    that makes the agent retry breaks this — the pass rate over 8 runs shows how often."""
    order = world.orders.pick(status="delivered")
    await run_agent(f"I want to return order {order.id} and get a refund", server=mcp_server)
    assert len(world.refunds.where(order_id=order.id)) == 1
