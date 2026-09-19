# Status

Active milestone: **Weekend 9** is next. Weekends 1–8 are done (through HTTP + second framework).
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
| 8 | HTTP transport; `worldbench serve`; second framework | done | 2026-09-19; reference mcp.Client drives the world over HTTP |
| 9 | hardening, docs, second example world | next | a stranger can write a world file |
| 10 | README demo, GIF, CI, PyPI 0.1.0 | todo | pip install works clean |
| 11 | launch: HN, MCP/Pydantic AI communities | todo | 20 users, 5 external issues |
| 12 | triage, roadmap (v0.2 replay, v0.3 scenario format) | todo | |

## Next session should
Weekend 9 — hardening, docs, and a second example world so a stranger can write a world file.
1. A second example world (a different domain, e.g. a support/ticketing or bank world) with
   its own README, exercising builtins + a custom handler + faults — proof the format
   generalises beyond shop.
2. User docs: a "write your own world" guide (schema reference: field types, operations,
   faults block, custom handlers), the pytest markers/fixtures reference, and the CLI.
3. Hardening: clearer errors on bad world files (unknown field type, bad handler path,
   duplicate record names already error — point at the offending key), YAML validation
   messages, and friendly failures in the plugin fixtures.

Handoff notes from weekend 8:
- HTTP: `serve_http(world, host, port, path="/mcp", ...)` runs `MCPServer.run("streamable-http")`.
  CLI: `worldbench serve <world> [--http] [--host] [--port] [--faults] [--run-index]
  [--state-file]` (stdio default). `worldbench.cli.main` is the entry; also `python -m
  worldbench.cli serve ...`.
- `mcp_url` fixture spawns `worldbench serve --http` on a free port, waits for the port, and
  yields a URL (a `str` subclass) with `.snapshot()` that reads the server's state-file mirror
  (the out-of-process world can't be shared). It applies `@pytest.mark.faults` only as
  `--faults` (world file's block); inline dict faults over HTTP aren't supported.
- Framework-neutral proof: `tests/test_http.py` drives the world over HTTP with the reference
  `mcp.Client` (not Pydantic AI). `mcp.Client(url).list_tools()` returns a result object — use
  `.tools`. A full second *agent framework* over HTTP (OpenAI Agents SDK / LangChain) is still
  open if you want a heavier example, but protocol-level neutrality is proven keyless.
- `--runs` known limitation still stands (no combining `@runs` with other parametrize markers).

## Blocked / open
- Live demo ran (gpt-5-mini, OpenAI key): happy path correct, and it correctly refuses the
  already-returned order 5. Finding: naive tools alone don't reliably break a competent
  agent — the double refund needs a forced retry (timeout), which is milestone 4's job.
  This raises the bar for the demo test: it's only meaningful once faults exist.
