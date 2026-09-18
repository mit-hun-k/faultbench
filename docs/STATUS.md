# Status

Active milestone: **Weekend 4** is next. Weekends 1 (toy agent), 2 (world engine), 3 (MCP server) are done.
Plain-language view for Mithun of what each milestone is and why: `docs/JOURNEY.md` (keep in sync).

| # | Milestone | State | Notes |
| - | --- | --- | --- |
| 0 | Scaffold: layout, pyproject, CLAUDE.md, docs, empty tests | done | 2026-09-19 |
| 1 | Toy refund agent (Pydantic AI) + 3 hand-written MCP tools over a dict | done | 2026-09-19; proves the problem from the agent side |
| 2 | world/: schema, engine, seed; unit tests | done | 2026-09-19; `World.load(...).orders.all()` byte-identical, verified cross-process |
| 3 | server/: generate get/list/create tools from YAML; stdio | done | 2026-09-19; toy agent completed a refund against the generated server (gpt-5-mini) |
| 4 | faults/: injector + clock; wire into server | next | reproduce the double-refund bug. DEMO POINT |
| 5 | pytest_plugin: world/faults/mcp_url fixtures, markers | todo | first green test |
| 6 | --runs=N pass rate; trace recorder + fixture | todo | "17/20 passed" output |
| 7 | custom ops, enum/datetime, conditional faults, rate limits | todo | sync-lag + eligibility tests |
| 8 | HTTP transport; `worldbench serve`; second framework | todo | framework-neutral proven |
| 9 | hardening, docs, second example world | todo | a stranger can write a world file |
| 10 | README demo, GIF, CI, PyPI 0.1.0 | todo | pip install works clean |
| 11 | launch: HN, MCP/Pydantic AI communities | todo | 20 users, 5 external issues |
| 12 | triage, roadmap (v0.2 replay, v0.3 scenario format) | todo | |

## Next session should
Weekend 4 — the demo milestone. Build `src/worldbench/faults/`: `clock.py` (`FakeClock`
with `now()`/`advance(seconds)`), `profile.py` (pydantic models for the `faults:` block,
already present in shop.yaml: `latency_ms`, `errors: {kind: prob}`, keyed by
`service.operation` or `default`), and `injector.py` (wraps an operation callable; seeded
RNG `seed + run_index`; error catalogue: timeout, http_500, http_429, malformed_json,
empty_result, not_found). Wire the injector + clock into `build_server` (both already take a
`clock` param; add a `faults`/injector param). Goal (JOURNEY): set "10% of refund calls
time out" and watch the toy agent refund a customer twice.

Handoff notes from weekend 3:
- `build_server(world, clock=None, state_file=None)` and `_make_tool_fn` already thread a
  `clock` through to custom handlers; wrap `call()` with the injector there.
- `shop_rules.create_return` enforces the 30-day window ONLY when `clock is not None`. Once
  FakeClock exists, decide its "now": seed datetimes are in a fixed 2020–2025 window, so a
  clock at ~2026 puts every order outside 30 days. Either set the clock inside the window or
  revisit the seed window so delivered-and-in-window orders exist for the demo.
- Faults must record every decision to the trace (trace recorder is weekend 6; for the
  weekend-4 demo, stderr logging like `_record` is enough).

## Blocked / open
- Live demo ran (gpt-5-mini, OpenAI key): happy path correct, and it correctly refuses the
  already-returned order 5. Finding: naive tools alone don't reliably break a competent
  agent — the double refund needs a forced retry (timeout), which is milestone 4's job.
  This raises the bar for the demo test: it's only meaningful once faults exist.
