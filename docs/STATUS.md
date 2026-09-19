# Status

Active milestone: **Weekend 10** is next. Weekends 1–9 are done (through hardening, docs, second world).
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
| 9 | hardening, docs, second example world | done | 2026-09-19; WORLDS.md + TESTING.md + examples/bank + friendly errors |
| 10 | README demo, GIF, CI, PyPI 0.1.0 | next | pip install works clean |
| 11 | launch: HN, MCP/Pydantic AI communities | todo | 20 users, 5 external issues |
| 12 | triage, roadmap (v0.2 replay, v0.3 scenario format) | todo | |

## Next session should
Weekend 10 — release 0.1.0. 
1. README: replace the illustrative demo block with the real, runnable one (the shop refund
   + the "5/6 passed" pass-rate output), a short GIF or asciinema of `uv run pytest
   examples/shop -k survives --faults`, and a 60-second quickstart. Bump `version` in
   pyproject to 0.1.0 and Development Status classifier.
2. CI: a GitHub Actions workflow running `uv sync --all-extras`, `uv run ruff check .`,
   `uv run pytest` (the key-free suite) on push/PR.
3. PyPI: confirm the wheel builds (`uv build`), metadata is right, and `pip install worldbench`
   works clean in a fresh venv. Publish 0.1.0.

Handoff notes from weekend 9:
- User docs: `docs/WORLDS.md` (write-your-own-world reference) and `docs/TESTING.md` (markers,
  fixtures, --runs, HTTP, CLI). README status/quickstart updated to point at them; the polished
  demo/GIF is this milestone's job.
- Second world: `examples/bank/` (accounts + `transfers` ledger, custom `transfer` handler,
  timeout fault). Validated keylessly by `tests/test_bank_example.py` so it stays working.
- Hardening: `World.load` gives friendly errors (missing file, invalid YAML, non-mapping);
  `parse_world` guards service/record/field shapes and names the offending record. Covered by
  `tests/test_errors.py`.
- 102 tests pass key-free; example agent tests still need a key (`uv run pytest examples/shop`).
- Known limitation unchanged: no combining `@runs` with other parametrize markers.

## Blocked / open
- Live demo ran (gpt-5-mini, OpenAI key): happy path correct, and it correctly refuses the
  already-returned order 5. Finding: naive tools alone don't reliably break a competent
  agent — the double refund needs a forced retry (timeout), which is milestone 4's job.
  This raises the bar for the demo test: it's only meaningful once faults exist.
