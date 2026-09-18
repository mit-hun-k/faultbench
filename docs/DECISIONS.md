# Decisions

One line each. Append; do not rewrite history. Format: date, decision, reason.

- 2026-09-19 — Name: `worldbench`. Reason: describes the thing (fake world + benchmarking); free on PyPI/GitHub at time of check.
- 2026-09-19 — License: Apache 2.0. Reason: matches peers (Scenario, DeepEval, tau2-bench), patent grant, leaves room for a hosted product later.
- 2026-09-19 — Language: Python 3.11+, packaged with uv. Reason: largest agent ecosystem; pytest is the natural runner.
- 2026-09-19 — Scope: fake world + faults + trace + pytest. Explicitly NOT simulated users, judges, dashboards. Reason: those markets are full; the environment layer is empty (see market doc).
- 2026-09-19 — Fake services are hand-written from YAML, not LLM-emulated. Reason: determinism is the feature. `kind: emulated` may come later on request.
- 2026-09-19 — Logic lives in Python handlers (`kind: custom`), never in YAML templating. Reason: every YAML feature is something users must learn and something that breaks sharing.
- 2026-09-19 — Server runs as a subprocess per test, stdio by default, HTTP when the agent is remote. Reason: isolation over speed at this stage.
- 2026-09-19 — Tests report a pass rate over N seeded runs; `min_pass_rate` converts to pass/fail for CI. Reason: agents are probabilistic; a single pass/fail lies.
- 2026-09-19 — Toy agent uses Pydantic AI. Reason: small, typed, speaks MCP natively, model-agnostic.
- 2026-09-19 — Time is read only from `FakeClock`. Reason: "order is 2 hours old" must be testable without waiting.
- 2026-09-19 — Installed `mcp` is 2.x (2.2.0): `FastMCP` is now `mcp.server.mcpserver.MCPServer` (`@server.tool()`, `server.run("stdio"|"streamable-http")`). Weekend 3 targets this API; `pyproject` `mcp>=1.2` should be tightened to `>=2` before the server milestone.
- 2026-09-19 — Pydantic AI is 2.x (2.45): MCP client is `MCPToolset(FastMCPClient(StdioTransport(...)))`, not `MCPServerStdio`. Agent connects via `async with agent:`.
- 2026-09-19 — Example agent model: `anthropic:claude-opus-5` (user choice for weekend 1). Swappable via `MODEL` in `examples/shop/agent.py`.
