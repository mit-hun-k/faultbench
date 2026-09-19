# Status

Active milestone: **Weekend 8** is next. Weekends 1–7 are done (through rules + smarter faults).
Plain-language view for Mithun of what each milestone is and why: `docs/JOURNEY.md` (keep in sync).

| # | Milestone | State | Notes |
| - | --- | --- | --- |
| 0 | Scaffold: layout, pyproject, CLAUDE.md, docs, empty tests | done | 2026-09-19 |
| 1 | Toy refund agent (Pydantic AI) + 3 hand-written MCP tools over a dict | done | 2026-09-19; proves the problem from the agent side |
| 2 | world/: schema, engine, seed; unit tests | done | 2026-09-19; `World.load(...).orders.all()` byte-identical, verified cross-process |
| 3 | server/: generate get/list/create tools from YAML; stdio | done | 2026-09-19; toy agent completed a refund against the generated server (gpt-5-mini) |
| 4 | faults/: injector + clock; wire into server | done | 2026-09-19; live agent double-refunded order 2 under a 10% timeout |
| 5 | pytest_plugin: world/faults/mcp_url fixtures, markers | done | 2026-09-19; first green refund test passes via fixtures/markers |
| 6 | --runs=N pass rate; trace recorder + fixture | done | 2026-09-19; live "5/6 passed (83%)" with a double-refund trace |
| 7 | custom ops, enum/datetime, conditional faults, rate limits | done | 2026-09-19; sync-lag + eligibility + rate-limit tests pass |
| 8 | HTTP transport; `worldbench serve`; second framework | next | framework-neutral proven |
| 9 | hardening, docs, second example world | todo | a stranger can write a world file |
| 10 | README demo, GIF, CI, PyPI 0.1.0 | todo | pip install works clean |
| 11 | launch: HN, MCP/Pydantic AI communities | todo | 20 users, 5 external issues |
| 12 | triage, roadmap (v0.2 replay, v0.3 scenario format) | todo | |

## Next session should
Weekend 8 — HTTP transport, `worldbench serve`, and a second framework (framework-neutral
proof). Three parts:
1. HTTP transport: `MCPServer.run("streamable-http")` exists. Add a streamable-HTTP serve
   path and an `mcp_url` fixture (a real URL to a server subprocess) alongside the in-process
   `mcp_server`. Note: an out-of-process server does NOT share the `world` object, so decide
   how tests assert on state over HTTP — likely read the server's state file (the server
   already mirrors `world.snapshot()` to `WORLDBENCH_STATE_FILE`), or expose a read path.
2. `worldbench serve`: flesh out `src/worldbench/cli.py` (currently a stub `main`) to run
   `worldbench serve <world.yaml> [--http] [--faults]`. Wire stdio + HTTP.
3. Second framework: prove an agent built with a different framework (not Pydantic AI) passes
   the same world over HTTP. Pick one that speaks MCP over HTTP; add a second example or a
   framework-neutral test. This is the "works with any framework" claim → fact.

Handoff notes from weekend 7:
- Clock is now threaded everywhere: `mcp_server` fixture and `serve_stdio` build with a
  FakeClock (default now = `world.seed.WORLD_EPOCH` = `faults.clock.DEFAULT_NOW` = 2025-06-01,
  drift-guarded by `test_rules.test_clock_matches_seed_epoch`). Seed datetimes fall in the 20
  days before the epoch, so delivered orders are eligible for return at the default clock.
  Tests move the clock (same object the server holds) to drive eligibility / sync lag.
- Conditional faults: `not_found_if_newer_than` enforced in the injector via a `record_time`
  the server computes (first datetime field of the target record, get/update/delete only).
- Rate limits: `rate_limit: {calls, per_seconds}` enforced in the injector (clock-driven
  http_429), parsed in `FaultRule`. Example (commented) in `shop.yaml`.
- Order of injector checks: latency → conditional not-found → rate limit → probabilistic
  error → execute. Conditional + rate limit are deterministic (no RNG).
- `--runs` known limitation still stands (no combining `@runs` with other parametrize markers).

## Blocked / open
- Live demo ran (gpt-5-mini, OpenAI key): happy path correct, and it correctly refuses the
  already-returned order 5. Finding: naive tools alone don't reliably break a competent
  agent — the double refund needs a forced retry (timeout), which is milestone 4's job.
  This raises the bar for the demo test: it's only meaningful once faults exist.
