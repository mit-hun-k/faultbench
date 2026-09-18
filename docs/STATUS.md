# Status

Active milestone: **Weekend 5** is next. Weekends 1–4 (toy agent, world engine, MCP server, faults) are done.
Plain-language view for Mithun of what each milestone is and why: `docs/JOURNEY.md` (keep in sync).

| # | Milestone | State | Notes |
| - | --- | --- | --- |
| 0 | Scaffold: layout, pyproject, CLAUDE.md, docs, empty tests | done | 2026-09-19 |
| 1 | Toy refund agent (Pydantic AI) + 3 hand-written MCP tools over a dict | done | 2026-09-19; proves the problem from the agent side |
| 2 | world/: schema, engine, seed; unit tests | done | 2026-09-19; `World.load(...).orders.all()` byte-identical, verified cross-process |
| 3 | server/: generate get/list/create tools from YAML; stdio | done | 2026-09-19; toy agent completed a refund against the generated server (gpt-5-mini) |
| 4 | faults/: injector + clock; wire into server | done | 2026-09-19; live agent double-refunded order 2 under a 10% timeout |
| 5 | pytest_plugin: world/faults/mcp_url fixtures, markers | next | first green test |
| 6 | --runs=N pass rate; trace recorder + fixture | todo | "17/20 passed" output |
| 7 | custom ops, enum/datetime, conditional faults, rate limits | todo | sync-lag + eligibility tests |
| 8 | HTTP transport; `worldbench serve`; second framework | todo | framework-neutral proven |
| 9 | hardening, docs, second example world | todo | a stranger can write a world file |
| 10 | README demo, GIF, CI, PyPI 0.1.0 | todo | pip install works clean |
| 11 | launch: HN, MCP/Pydantic AI communities | todo | 20 users, 5 external issues |
| 12 | triage, roadmap (v0.2 replay, v0.3 scenario format) | todo | |

## Next session should
Weekend 5 — build `src/worldbench/pytest_plugin.py`: fixtures `world`, `faults`, `clock`,
`mcp_url` (server subprocess per test), and markers `@pytest.mark.world("path.yaml")`,
`@pytest.mark.faults("path" | dict)`, `@pytest.mark.runs(N)`, `@pytest.mark.min_pass_rate`.
Goal (JOURNEY): a first green refund test against a fault-free world. `--runs=N` / pass-rate
reporting is weekend 6, so keep this to fixtures + markers + one green test.

Handoff notes from weekend 4:
- `build_server(world, clock=None, state_file=None, faults=None, run_index=0)` exists and is
  wired; the `mcp_url` fixture can spawn `python -m worldbench.server <world> [--faults]`
  (env: WORLDBENCH_STATE_FILE, WORLDBENCH_FAULTS=1, WORLDBENCH_RUN_INDEX). But `mcp_url`
  implies HTTP (a URL); stdio is a subprocess with no URL. Decide: expose an HTTP transport
  now (ARCHITECTURE §3 lists streamable HTTP; `MCPServer.run("streamable-http")` exists), or
  make the fixture hand back a stdio transport/connected toolset instead of a URL. HTTP is
  formally weekend 8 — leaning toward a stdio-based fixture for weekend 5, revisit naming.
- The `world` fixture must be the SAME world the server mutates so tests can assert on it.
  With a subprocess that's two processes; either run the server in-process (build_server +
  in-memory client, as the tests already do) and share the World object, or read the
  server's state file. In-process/in-memory is simplest for a first green test.
- Clock/seed-window consistency is still deferred to weekend 7 (conditional faults +
  eligibility). FakeClock is built and unit-tested; nothing enforces the window yet.
- Trace recorder is weekend 6; the injector already takes an `on_event` hook to feed it.

## Blocked / open
- Live demo ran (gpt-5-mini, OpenAI key): happy path correct, and it correctly refuses the
  already-returned order 5. Finding: naive tools alone don't reliably break a competent
  agent — the double refund needs a forced retry (timeout), which is milestone 4's job.
  This raises the bar for the demo test: it's only meaningful once faults exist.
