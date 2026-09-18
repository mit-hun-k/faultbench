# Status

Active milestone: **Weekend 6** is next. Weekends 1–5 (toy agent, world engine, MCP server, faults, pytest plugin) are done.
Plain-language view for Mithun of what each milestone is and why: `docs/JOURNEY.md` (keep in sync).

| # | Milestone | State | Notes |
| - | --- | --- | --- |
| 0 | Scaffold: layout, pyproject, CLAUDE.md, docs, empty tests | done | 2026-09-19 |
| 1 | Toy refund agent (Pydantic AI) + 3 hand-written MCP tools over a dict | done | 2026-09-19; proves the problem from the agent side |
| 2 | world/: schema, engine, seed; unit tests | done | 2026-09-19; `World.load(...).orders.all()` byte-identical, verified cross-process |
| 3 | server/: generate get/list/create tools from YAML; stdio | done | 2026-09-19; toy agent completed a refund against the generated server (gpt-5-mini) |
| 4 | faults/: injector + clock; wire into server | done | 2026-09-19; live agent double-refunded order 2 under a 10% timeout |
| 5 | pytest_plugin: world/faults/mcp_url fixtures, markers | done | 2026-09-19; first green refund test passes via fixtures/markers |
| 6 | --runs=N pass rate; trace recorder + fixture | next | "17/20 passed" output |
| 7 | custom ops, enum/datetime, conditional faults, rate limits | todo | sync-lag + eligibility tests |
| 8 | HTTP transport; `worldbench serve`; second framework | todo | framework-neutral proven |
| 9 | hardening, docs, second example world | todo | a stranger can write a world file |
| 10 | README demo, GIF, CI, PyPI 0.1.0 | todo | pip install works clean |
| 11 | launch: HN, MCP/Pydantic AI communities | todo | 20 users, 5 external issues |
| 12 | triage, roadmap (v0.2 replay, v0.3 scenario format) | todo | |

## Next session should
Weekend 6 — pass rate + trace. Two parts:
1. `src/worldbench/trace/`: `recorder.py` (JSON Lines, one event per tool call:
   `{run, seq, ts, tool, args, fault, latency_ms, ok, result|error, world_rev}`) and
   `queries.py` (`Trace.count(tool)`, `calls_to(tool)`, `faults()`, `failures()`). Wire the
   recorder into `build_server`/the injector: the injector already takes an `on_event` hook,
   and `_record` in mcp_server.py is the success path — feed both into the recorder.
2. Plugin: honour `@pytest.mark.runs(N)` / `--runs=N` by running a test N times with
   `run_index = 0..N-1` (distinct deterministic fault sequences), report
   `runs / passed / failed / pass rate` and a per-failure trace summary, and turn
   `@pytest.mark.min_pass_rate(r)` into an overall pass/fail. Add a `trace` fixture.
Goal (JOURNEY): print "17/20 passed, 3 duplicate refunds after a timeout" with a readable
trace per failure.

Handoff notes from weekend 5:
- Fixtures live in `pytest_plugin.py`: `world`, `faults` (empty unless `@pytest.mark.faults`),
  `clock` (a standalone FakeClock), `mcp_server` (in-process server sharing the `world`
  object). No HTTP/`mcp_url` yet — that's weekend 8. The example agent connects to the
  in-memory server via `run_agent(..., server=mcp_server)` (agent.build_toolset grew a
  `server=` arg).
- IMPORTANT: `mcp_server` builds with `clock=None` on purpose. Threading the `clock` fixture
  in activates `create_return`'s 30-day window, and the seed dates (2020–2025) fall outside
  30 days of the default clock (2025-06-01), so the agent correctly refuses and the refund
  test fails. Aligning seed dates with the clock (or setting the clock into the seed window)
  is the weekend-7 eligibility work; do it before threading the clock into the server.
- Two test locations: `uv run pytest` runs `tests/` (no key; includes `tests/test_plugin.py`
  driving fixtures via `tests/worlds/mini.yaml`). `uv run pytest examples/shop` runs the real
  agent test `examples/shop/test_refunds.py` (skips without a model key; `conftest.py` loads
  `.env`). For `--runs=N` demoing the double refund, target the example test with a faults
  marker once weekend 6 lands.
- The `runs`/`min_pass_rate` markers are registered but not yet enforced.

## Blocked / open
- Live demo ran (gpt-5-mini, OpenAI key): happy path correct, and it correctly refuses the
  already-returned order 5. Finding: naive tools alone don't reliably break a competent
  agent — the double refund needs a forced retry (timeout), which is milestone 4's job.
  This raises the bar for the demo test: it's only meaningful once faults exist.
