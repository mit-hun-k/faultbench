"""Framework-neutrality with a real second agent framework: the OpenAI Agents SDK drives the
shop world over HTTP (not Pydantic AI). Proves faultbench is a plain MCP server any framework
can test against.

Needs the OpenAI Agents SDK and a key:  pip install openai-agents  (+ OPENAI_API_KEY)
Run: uv run --with openai-agents pytest examples/shop/test_openai_agents.py
"""

import os

import pytest

pytest.importorskip("agents", reason="needs the OpenAI Agents SDK (pip install openai-agents)")

pytestmark = pytest.mark.skipif(not os.environ.get("OPENAI_API_KEY"), reason="needs OPENAI_API_KEY")

INSTRUCTIONS = (
    "You are a refund-support agent for an online shop. To handle a request: look the order "
    "up, create the return, then issue a refund for the order's full total. Never refund an "
    "order more than once. Be concise."
)


@pytest.mark.world("worlds/shop.yaml")
async def test_openai_agents_sdk_over_http(world, mcp_url):
    from agents import Agent, Runner
    from agents.mcp import MCPServerStreamableHttp, MCPServerStreamableHttpParams

    order = world.orders.pick(status="delivered")  # same seed => same id the served world has
    server = MCPServerStreamableHttp(params=MCPServerStreamableHttpParams(url=str(mcp_url)))
    async with server:
        agent = Agent(
            name="refunds", model="gpt-5-mini", instructions=INSTRUCTIONS, mcp_servers=[server]
        )
        await Runner.run(agent, f"Return order {order.id} and refund me.")

    snapshot = mcp_url.snapshot()  # the out-of-process world's end state
    assert snapshot["orders"][order.id]["status"] == "returned"
    refunds = [r for r in snapshot["refunds"].values() if r["order_id"] == order.id]
    assert len(refunds) == 1
