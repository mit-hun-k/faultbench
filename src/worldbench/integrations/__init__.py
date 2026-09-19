"""Optional, framework-specific adapters for connecting an agent to a worldbench server.

These are convenience only — worldbench's core is framework-neutral (it serves standard MCP).
Import the adapter for your framework, e.g. `from worldbench.integrations.pydantic_ai import
run_agent`. Each adapter needs its framework installed (an optional dependency).
"""
