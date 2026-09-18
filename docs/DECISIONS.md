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
- 2026-09-19 — Example agent model is set via `WORLDBENCH_DEMO_MODEL` (default `openai:gpt-5-mini`; the key on hand this session was OpenAI). Provider prefix picks the required key. Reason: keep the example key-agnostic rather than pinning one provider.
- 2026-09-19 — Schema pydantic root is `WorldSpec` (with `ServiceSpec`/`RecordType`/`FieldType`/`OperationSpec`/`SeedSpec`), not `World`. Reason: avoid two classes named `World` — `engine.World` is the runtime, stateful world.
- 2026-09-19 — Tables are reached on the runtime `World` by record-type name (`world.orders`), so record names must be unique across the world (validated). `shop.yaml` records are named as collections (`orders`, `refunds`). Reason: matches the documented target test `world.orders.pick(...)` / `world.refunds.where(...)` with no pluralization magic ("no clever" rule).
- 2026-09-19 — Seeded `datetime` fields are drawn from a FIXED absolute window (2020–2025), never a now-relative one, and stored as ISO strings. Reason: the byte-identical invariant must hold on any day; verified identical across two separate processes.
- 2026-09-19 — Seeding does not bump `revision`; a freshly loaded world is at revision 0. Only insert/update/delete bump it. Reason: revision should count agent-caused writes, not initial state.
- 2026-09-19 — MCP tool schemas are derived by giving a generated wrapper function an explicit `__signature__` (mcp 2.x `func_metadata` reads `inspect.signature`), one tool per operation. Reason: operations are known only at runtime from YAML; this reuses the SDK's schema generation instead of hand-building JSON schema.
- 2026-09-19 — Tool params: get/delete → `id`; update → `id` + optional fields; create → record fields (optional, id auto-assigned); list → the operation's `filter` fields (optional); custom → the handler's params minus `world`/`clock`. Create/list fields are optional so the agent can call with only what it knows (e.g. `issue_refund(order_id, amount)`). Reason: keep the toy agent working unchanged.
- 2026-09-19 — Business-rule failures (ValueError/LookupError/KeyError from an op or handler) are converted to MCP `ToolError`; other exceptions propagate as crashes. Reason: the agent sees a clean, readable tool error for "not found"/"not delivered" without a server traceback, while real bugs stay loud.
- 2026-09-19 — Custom handler modules resolve by bare name; the server puts the world file's directory and its parent on `sys.path`. Reason: lets `shop.yaml` (in worlds/) reference `shop_rules` (in examples/shop/) without packaging.
- 2026-09-19 — `examples/shop/tools_dict.py` deleted; the agent now spawns `python -m worldbench.server <world.yaml>`. Reason: the generated server replaces the milestone-1 throwaway.
