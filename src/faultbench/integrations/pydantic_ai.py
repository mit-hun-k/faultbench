"""Pydantic AI adapter: connect an agent to a faultbench server in one line.

Needs Pydantic AI:  pip install 'faultbench[pydantic-ai]'

`mcp` is whatever the pytest fixtures give you — an in-process server (`mcp_server`) or an
HTTP URL (`mcp_url`); the same helpers work with both, so tests read the same either way.

    from faultbench.integrations.pydantic_ai import run_agent

    @pytest.mark.world("world.yaml")
    async def test_refund(world, mcp_server):
        order = world.orders.pick(status="delivered")
        await run_agent("openai:gpt-5-mini", f"Refund order {order.id}", mcp=mcp_server,
                        system_prompt="You are a refund agent.")
        assert len(world.refunds.where(order_id=order.id)) == 1
"""

from __future__ import annotations

from typing import Any

try:
    from pydantic_ai import Agent
    from pydantic_ai.mcp import FastMCPClient, MCPToolset
except ImportError as exc:  # pragma: no cover - exercised only without a suitable version
    raise ImportError(
        "faultbench.integrations.pydantic_ai needs a recent Pydantic AI (v2+, tested with "
        "2.45+). Install it with: pip install 'faultbench[pydantic-ai]'"
    ) from exc


def toolset(mcp: Any) -> MCPToolset:
    """A Pydantic AI toolset for a faultbench server. `mcp` is an in-process MCPServer (the
    `mcp_server` fixture) or an HTTP URL string (the `mcp_url` fixture)."""
    return MCPToolset(FastMCPClient(str(mcp) if not _is_server(mcp) else mcp))


def agent(model: str, mcp: Any, *, system_prompt: str = "", **agent_kwargs: Any) -> Agent:
    """A Pydantic AI Agent wired to a faultbench server."""
    return Agent(model, system_prompt=system_prompt, toolsets=[toolset(mcp)], **agent_kwargs)


async def run_agent(
    model: str, prompt: str, *, mcp: Any, system_prompt: str = "", **agent_kwargs: Any
) -> str:
    """Run one request end to end against a faultbench server; return the agent's reply."""
    the_agent = agent(model, mcp, system_prompt=system_prompt, **agent_kwargs)
    async with the_agent:
        result = await the_agent.run(prompt)
    return result.output


def _is_server(mcp: Any) -> bool:
    # A URL/path is a str; anything else is treated as an in-process server object.
    return not isinstance(mcp, str)
