# Status

Active milestone: **Weekend 2** is next. Weekend 1 (toy refund agent + naive dict server) is done.

| # | Milestone | State | Notes |
| - | --- | --- | --- |
| 0 | Scaffold: layout, pyproject, CLAUDE.md, docs, empty tests | done | 2026-09-19 |
| 1 | Toy refund agent (Pydantic AI) + 3 hand-written MCP tools over a dict | done | 2026-09-19; proves the problem from the agent side |
| 2 | world/: schema, engine, seed; unit tests | next | `World.load("shop.yaml").orders.all()` is deterministic |
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
Weekend 2. Build `src/worldbench/world/`: `schema.py` (pydantic models for World/Service/
RecordType/Field/Operation/SeedSpec per ARCHITECTURE §1), `engine.py` (`World.load(path)`,
`Table` with get/all/where/pick/insert/update/delete, `World.snapshot/diff/revision`), and
`seed.py` (faker generators per field type, seeded by `world.seed`; CSV/JSON loaders).
Target: `World.load("examples/shop/worlds/shop.yaml").orders.all()` is deterministic — same
YAML + same seed => byte-identical initial state. Write unit tests in `tests/`. Do not build
the server yet (that's weekend 3). `shop.yaml` already has the target schema shape to load.

## Blocked / open
- Live model demo (`examples/shop/demo.py`) was NOT run this session: no ANTHROPIC_API_KEY
  in the env. Plumbing was verified keyless (server subprocess, tool schemas, state file,
  and the double-refund failure all confirmed). Run `demo.py` once with a key to watch how
  Opus 5 handles it — worth a look before the engine hides these tools behind YAML.
