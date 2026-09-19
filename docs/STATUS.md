# Status

Active milestone: **Weekend 7** is next. Weekends 1–6 (toy agent, world engine, MCP server, faults, pytest plugin, pass rate + trace) are done.
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
| 7 | custom ops, enum/datetime, conditional faults, rate limits | next | sync-lag + eligibility tests |
| 8 | HTTP transport; `worldbench serve`; second framework | todo | framework-neutral proven |
| 9 | hardening, docs, second example world | todo | a stranger can write a world file |
| 10 | README demo, GIF, CI, PyPI 0.1.0 | todo | pip install works clean |
| 11 | launch: HN, MCP/Pydantic AI communities | todo | 20 users, 5 external issues |
| 12 | triage, roadmap (v0.2 replay, v0.3 scenario format) | todo | |

## Next session should
Weekend 7 — custom ops polish + conditional faults + eligibility, and the clock alignment.
1. Enforce conditional faults: `not_found_if_newer_than: 2h` (already parsed into
   `FaultRule.conditional`). The injector needs the record's timestamp and the clock to
   decide; wire the clock through and implement the not-found-if-recent behaviour.
2. Clock/seed-window alignment (the item deferred since weekend 4): make the seed datetimes
   consistent with the FakeClock's 'now' so `create_return`'s 30-day window has eligible
   delivered orders, then thread the `clock` fixture into `mcp_server` (currently `clock=None`
   in `pytest_plugin.py`). Add an eligibility test (delivered-but-old order is refused).
3. Rate limits: `rate_limit: {calls, per_seconds}` — parse (profile currently ignores it) and
   enforce in the injector (http_429 after N calls per window; clock-driven).
4. enum/datetime handling polish as needed for the above.
Goal (JOURNEY §7): sync-lag (not_found_if_newer_than) and eligibility tests pass.

Handoff notes from weekend 6:
- Trace: `worldbench.trace.Recorder` (JSONL, event per call) + `Trace` queries
  (count/calls_to/faults/failures/summary). `build_server(..., recorder=)` records every
  call; the injector's `call(..., on_decision=)` reports the fault kind + latency.
- Plugin fixtures now include `trace` (live view) and a private `_recorder`. `@runs(N)` /
  `--runs=N` parametrise `run_index` 0..N-1; each run is a normal pytest item (async works).
  Pass-rate + per-failure trace print in the terminal summary. `min_pass_rate(r)` absorbs
  individual run failures (flips them to passed in `pytest_runtest_makereport`) and the
  session fails only if the aggregate rate < r (`pytest_sessionfinish`). Empty groups
  (deselected by -k) are skipped so they neither print nor fail CI.
- `--runs` is global: it parametrises every test that (transitively) uses `run_index` (i.e.
  uses `mcp_server`). Combining `--runs` with `-k`/`-x` trims a group; reporting is over what
  ran. Known limitation: combining `@runs` with other parametrize markers on one test isn't
  supported (group key strips only the `[run..]` id).
- Live demo: `uv run pytest examples/shop -k survives --runs=6` → "5/6 passed (83%)" with a
  `issue_refund!timeout → issue_refund` double-refund trace.

## Blocked / open
- Live demo ran (gpt-5-mini, OpenAI key): happy path correct, and it correctly refuses the
  already-returned order 5. Finding: naive tools alone don't reliably break a competent
  agent — the double refund needs a forced retry (timeout), which is milestone 4's job.
  This raises the bar for the demo test: it's only meaningful once faults exist.
