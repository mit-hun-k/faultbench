# faultbench

Fake, stateful worlds with fault injection for testing tool-using AI agents.
A user declares services and records in `world.yaml`; faultbench serves them as MCP
tools, injects latency/errors/clock skew on demand, records every call, and lets
pytest assert on the world's end state.

**Read `docs/STATUS.md` before doing anything.** It says which milestone is active
and what the next session should do. Then read `docs/ARCHITECTURE.md` for the
component you are touching and `docs/DECISIONS.md` so you don't re-argue settled choices.

## Non-goals (do not build these)
- No simulated user / persona engine. Users bring LangWatch Scenario, DeepEval or openevals.
- No LLM judge or transcript scoring. Assert on world state and the trace only.
- No dashboard or web UI. Stay inside pytest and the CLI.
- No clever YAML. Logic goes in Python handlers, not in templates or conditionals.
- No support for every framework at once. Pydantic AI first, one more via HTTP, then stop.

## Stack
Python 3.11+, uv, pydantic v2, official `mcp` SDK, faker, pytest, ruff. No database.
Target: under 3,000 lines for v0.1.

## Commands
    uv sync --all-extras          # install
    uv run pytest                 # harness unit tests
    uv run pytest examples/shop   # example agent tests (needs a model API key)
    uv run ruff check . && uv run ruff format .
    uv run faultbench serve examples/shop/worlds/shop.yaml

## Session protocol
1. Read STATUS.md, ARCHITECTURE.md (relevant section), DECISIONS.md.
2. Propose a short plan for this session's milestone; wait for approval.
3. One component per session. Do not start the next milestone.
4. Write tests alongside code in `tests/`.
5. Before ending: run `uv run pytest` and `uv run ruff check .`, update STATUS.md
   (state + "next session should"), append to DECISIONS.md if anything was decided,
   and update docs/JOURNEY.md: flip the finished milestone to ✅ with a 2-line plain-language
   "Built." note (what exists now, not how), move the "Now" marker to the next one. Commit.

## Layout
    src/faultbench/world/    schema.py engine.py seed.py       # YAML -> stateful tables
    src/faultbench/faults/   profile.py injector.py clock.py   # latency, errors, fake time
    src/faultbench/server/   mcp_server.py operations.py       # world -> MCP tools
    src/faultbench/trace/    recorder.py queries.py            # JSONL trace of every call
    src/faultbench/pytest_plugin.py                            # fixtures, markers, --runs
    src/faultbench/cli.py                                      # `faultbench serve`
    examples/shop/           the refund agent demo (world, rules, agent, tests)
    tests/                   unit tests for faultbench itself
    docs/                    ARCHITECTURE, DECISIONS, STATUS, user docs

Background (why this exists, market landscape, 12-weekend plan):
https://claude.ai/code/artifact/058e73f3-39fa-4d36-8f96-f1b29efe8de2
