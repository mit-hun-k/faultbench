# Status

Active milestone: **Weekend 1**. Nothing built yet beyond the scaffold.

| # | Milestone | State | Notes |
| - | --- | --- | --- |
| 0 | Scaffold: layout, pyproject, CLAUDE.md, docs, empty tests | done | 2026-09-19 |
| 1 | Toy refund agent (Pydantic AI) + 3 hand-written MCP tools over a dict | next | proves the problem from the agent side |
| 2 | world/: schema, engine, seed; unit tests | todo | `World.load("shop.yaml").orders.all()` is deterministic |
| 3 | server/: generate get/list/create tools from YAML; stdio | todo | toy agent works unchanged against generated server |
| 4 | faults/: injector + clock; wire into server | todo | reproduce the double-refund bug. DEMO POINT |
| 5 | pytest_plugin: world/faults/mcp_url fixtures, markers | todo | first green test |
| 6 | --runs=N pass rate; trace recorder + fixture | todo | "17/20 passed" output |
| 7 | custom ops, enum/datetime, conditional faults, rate limits | todo | sync-lag + eligibility tests |
| 8 | HTTP transport; `worldbench serve`; second framework | todo | framework-neutral proven |
| 9 | hardening, docs, second example world | todo | a stranger can write a world file |
| 10 | README demo, GIF, CI, PyPI 0.1.0 | todo | pip install works clean |
| 11 | launch: HN, MCP/Pydantic AI communities | todo | 20 users, 5 external issues |
| 12 | triage, roadmap (v0.2 replay, v0.3 scenario format) | todo | |

## Next session should
Weekend 1. In `examples/shop/`: write `agent.py` (Pydantic AI agent with a refund-support
system prompt), a throwaway `tools_dict.py` MCP server exposing `get_order`, `create_return`,
`issue_refund` over a plain dict with ~5 orders, and a `demo.py` that runs "return order 3 and
refund me" end to end. Do not touch `src/` yet. Goal is to feel the problem, not to build the engine.
Pick a cheap model for the agent; read `.env.example`.

## Blocked / open
- Scaffold was verified by import/compile only: `uv sync` and `uv run pytest` could not run in the
  session that created it (no package index reachable). First thing in weekend 1: run
  `uv sync --all-extras && uv run pytest` on your Mac and confirm 3 smoke tests pass. Fix anything that doesn't.
