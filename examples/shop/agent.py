"""Refund-support agent for the shop demo (worldbench milestone 1).

A Pydantic AI agent that talks to the throwaway `tools_dict.py` MCP server over stdio.
It knows nothing about worldbench; it just sees three MCP tools. The whole point of
milestone 1 is to watch a real model drive these naive tools and see where it goes wrong.

Model: Claude Opus 5 (`anthropic:claude-opus-5`). Needs ANTHROPIC_API_KEY in the env
(see .env.example). Nothing in worldbench itself makes LLM calls — only this example does.
"""

from __future__ import annotations

import sys
from pathlib import Path

from pydantic_ai import Agent
from pydantic_ai.mcp import FastMCPClient, MCPToolset, StdioTransport

MODEL = "anthropic:claude-opus-5"

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


def build_toolset(server_path: str | None = None, state_file: str | None = None) -> MCPToolset:
    """Spawn `tools_dict.py` as a stdio MCP subprocess and expose it as a toolset."""
    server_path = server_path or str(Path(__file__).with_name("tools_dict.py"))
    env = {"SHOP_STATE_FILE": state_file} if state_file else None
    transport = StdioTransport(command=sys.executable, args=[server_path], env=env)
    return MCPToolset(FastMCPClient(transport))


def build_agent(toolset: MCPToolset) -> Agent:
    return Agent(MODEL, system_prompt=SYSTEM_PROMPT, toolsets=[toolset])


async def run_agent(prompt: str, state_file: str | None = None) -> str:
    """Run one request end to end and return the agent's final text reply."""
    toolset = build_toolset(state_file=state_file)
    agent = build_agent(toolset)
    async with agent:
        result = await agent.run(prompt)
    return result.output
