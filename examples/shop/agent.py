"""Refund-support agent for the shop demo.

A Pydantic AI agent that talks to a faultbench MCP server over stdio. As of milestone 3 the
server is *generated from* `worlds/shop.yaml` (`python -m faultbench.server`), replacing the
throwaway `tools_dict.py`. The agent itself is unchanged: it just sees three MCP tools.

Model: set via FAULTBENCH_DEMO_MODEL (default `openai:gpt-5-mini`); e.g.
`anthropic:claude-opus-5`. Needs the matching provider key in the env (see .env.example).
Nothing in faultbench itself makes LLM calls — only this example does.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from pydantic_ai import Agent
from pydantic_ai.mcp import FastMCPClient, MCPToolset, StdioTransport

from faultbench.integrations.pydantic_ai import toolset as wb_toolset

MODEL = os.environ.get("FAULTBENCH_DEMO_MODEL", "openai:gpt-5-mini")
DEFAULT_WORLD = str(Path(__file__).parent / "worlds" / "shop.yaml")

SYSTEM_PROMPT = """\
You are a refund-support agent for an online shop. You help customers return orders and
get their money back, using the tools provided.

Policy:
- Only orders that have been delivered are eligible for return and refund.
- To process a request: look the order up, create the return, then issue a refund for the
  order's full total.
- Never refund an order more than once.
- If an order is not eligible (not delivered, or already returned), explain why and do not
  issue a refund.

Be concise. Tell the customer what you did or why you could not help."""


def build_toolset(
    world_path: str | None = None,
    state_file: str | None = None,
    faults: bool = False,
    run_index: int = 0,
    server: object | None = None,
) -> MCPToolset:
    """Expose a faultbench server as a Pydantic AI toolset.

    If `server` (an in-process MCPServer, e.g. from the pytest `mcp_server` fixture) is given,
    connect to it in memory via the faultbench helper. Otherwise spawn `python -m
    faultbench.server` as a subprocess (this demo's way of running a live faulty world).
    """
    if server is not None:
        return wb_toolset(server)
    world_path = world_path or DEFAULT_WORLD
    env: dict[str, str] = {}
    if state_file:
        env["FAULTBENCH_STATE_FILE"] = state_file
    if faults:
        env["FAULTBENCH_FAULTS"] = "1"
        env["FAULTBENCH_RUN_INDEX"] = str(run_index)
    transport = StdioTransport(
        command=sys.executable,
        args=["-m", "faultbench.server", world_path],
        env=env or None,
    )
    return MCPToolset(FastMCPClient(transport))


def build_agent(toolset: MCPToolset) -> Agent:
    return Agent(MODEL, system_prompt=SYSTEM_PROMPT, toolsets=[toolset])


async def run_agent(
    prompt: str,
    state_file: str | None = None,
    world_path: str | None = None,
    faults: bool = False,
    run_index: int = 0,
    server: object | None = None,
) -> str:
    """Run one request end to end and return the agent's final text reply."""
    toolset = build_toolset(
        world_path=world_path,
        state_file=state_file,
        faults=faults,
        run_index=run_index,
        server=server,
    )
    agent = build_agent(toolset)
    async with agent:
        result = await agent.run(prompt)
    return result.output
