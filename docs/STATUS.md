# Status

Active milestone: **Weekend 3** is next. Weekends 1 (toy agent) and 2 (world engine) are done.
Plain-language view for Mithun of what each milestone is and why: `docs/JOURNEY.md` (keep in sync).

| # | Milestone | State | Notes |
| - | --- | --- | --- |
| 0 | Scaffold: layout, pyproject, CLAUDE.md, docs, empty tests | done | 2026-09-19 |
| 1 | Toy refund agent (Pydantic AI) + 3 hand-written MCP tools over a dict | done | 2026-09-19; proves the problem from the agent side |
| 2 | world/: schema, engine, seed; unit tests | done | 2026-09-19; `World.load(...).orders.all()` byte-identical, verified cross-process |
| 3 | server/: generate get/list/create tools from YAML; stdio | next | toy agent works unchanged against generated server |
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
Weekend 3. Build `src/worldbench/server/`: `mcp_server.py` (build an `mcp` 2.x `MCPServer`
from a World, one tool per operation, JSON schema derived from the record type; stdio
transport) and `operations.py` (built-in kinds get/list/create/update/delete; `custom`
resolves `handler: "module.func"` and calls `func(world, clock, **args)`). Goal: the toy
agent (`examples/shop/agent.py`) works UNCHANGED against a server generated from
`shop.yaml`, replacing `tools_dict.py`. Note: `create_return`'s handler expects a
`clock` and treats `placed_at` as a datetime, but seed writes ISO strings and there is no
clock until weekend 4 — for weekend 3 pass a real-`datetime.now` shim or defer the window
check; don't pull weekend-4 work forward. Tighten `pyproject` `mcp>=1.2` to `>=2` (API
moved to `mcp.server.mcpserver.MCPServer`). Do not build faults yet.

## Blocked / open
- Live demo ran (gpt-5-mini, OpenAI key): happy path correct, and it correctly refuses the
  already-returned order 5. Finding: naive tools alone don't reliably break a competent
  agent — the double refund needs a forced retry (timeout), which is milestone 4's job.
  This raises the bar for the demo test: it's only meaningful once faults exist.
