# Status

Active milestone: **Weekend 10 (release 0.1.0)** — local prep DONE; remote push + PyPI publish
are held for the user (new GitHub account `mit-hun-k` token, and explicit go on the irreversible
publish). Weekends 1–9 done.
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
| 8 | HTTP transport; `faultbench serve`; second framework | done | 2026-09-19; reference mcp.Client drives the world over HTTP |
| 9 | hardening, docs, second example world | done | 2026-09-19; WORLDS.md + TESTING.md + examples/bank + friendly errors |
| 10 | README demo, GIF, CI, PyPI 0.1.0 | wip | 2026-09-19; pushed to private github.com/mit-hun-k/faultbench, CI green; PyPI publish still pending |
| 11 | launch: HN, MCP/Pydantic AI communities | todo | 20 users, 5 external issues |
| 12 | triage, roadmap (v0.2 replay, v0.3 scenario format) | todo | |

## Next session should
Finish Weekend 10 release (the outward-facing, held steps), then Weekend 11 (launch).
Release steps still to do — all need the new account and/or an explicit go:
1. Add the git remote for `mit-hun-k` (user supplies the token via `!`, keeps it out of the
   transcript), then `git push -u origin main`. CI (`.github/workflows/ci.yml`) then runs.
2. Publish to PyPI — IRREVERSIBLE. `uv build` already produces clean `dist/faultbench-0.1.0.*`
   and it installs clean in a fresh venv (core deps only; `faultbench --version` -> 0.1.0).
   Publish with `uv publish` (needs a PyPI token) ONLY after the user confirms.
3. Optional: a real asciinema/GIF of `uv run pytest examples/shop -k survives --faults` for
   the README (can't be generated headlessly here; do on the user's machine).

Pre-launch validation (this session): drove the shop world with a REAL second framework, the
OpenAI Agents SDK, over HTTP (`examples/shop/test_openai_agents.py`, opt-in, `openai-agents`
extra) — clean refund fault-free; under a forced timeout it wrote 3 phantom refunds while
reporting failure, and faultbench caught them. That surfaced a genuine bug: the state-file
mirror only ran on success, so faulted writes (write-then-timeout) were under-reported over
HTTP — fixed (mirror on every attempt) and regression-tested
(`test_faulted_write_is_mirrored_to_state_file`). Also documented the enum-in-flow-YAML gotcha.

Done this session (local): `run_agent` helper in `faultbench.integrations.pydantic_ai`
(`toolset`/`agent`/`run_agent`, accepts in-process `mcp_server` OR the `mcp_url` string);
`pydantic-ai` extra; dogfooded in `examples/shop` + `docs/TESTING.md` + README; version bumped
to 0.1.0 (guarded by `test_version_matches_pyproject`); CI workflow file written; wheel built
and verified in a clean venv.

Handoff notes:
- 106 tests pass key-free; example agent tests need a key (`uv run pytest examples/shop`).
- The helper needs the `pydantic-ai` extra; core install stays framework-neutral.
- Known limitation unchanged: no combining `@runs` with other parametrize markers.

## Blocked / open
- Live demo ran (gpt-5-mini, OpenAI key): happy path correct, and it correctly refuses the
  already-returned order 5. Finding: naive tools alone don't reliably break a competent
  agent — the double refund needs a forced retry (timeout), which is milestone 4's job.
  This raises the bar for the demo test: it's only meaningful once faults exist.
