"""Optional, framework-specific adapters for connecting an agent to a faultbench server.

These are convenience only — faultbench's core is framework-neutral (it serves standard MCP).
Import the adapter for your framework, e.g. `from faultbench.integrations.pydantic_ai import
run_agent`. Each adapter needs its framework installed (an optional dependency).
"""
