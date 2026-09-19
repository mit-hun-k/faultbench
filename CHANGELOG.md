# Changelog

## 0.1.1
- Add project URLs (Homepage / Repository / Issues) to the package metadata.

## 0.1.0
First public release. Declare fake, stateful worlds in YAML; serve them as MCP tools over
stdio or HTTP; inject latency, errors, timeouts, rate limits, and clock-driven faults; record
a JSONL trace; and assert on world state from pytest across N seeded runs with a pass rate.
- `world/`: schema, deterministic seeded engine (`World.load`, tables, snapshot/diff).
- `faults/`: `FakeClock`, fault profile, seeded injector (probabilistic + conditional + rate).
- `server/`: MCP server generated from a world; `faultbench serve` (stdio / streamable HTTP).
- `trace/`: JSONL recorder + `Trace` queries.
- pytest plugin: `world`/`faults`/`clock`/`mcp_server`/`mcp_url`/`trace` fixtures, `@world`/
  `@faults`/`@runs`/`@min_pass_rate` markers, `--runs=N` pass-rate reporting.
- `integrations.pydantic_ai`: one-line `run_agent` helper.
- Examples: shop (refund agent), bank, stripe (payments). Validated with Pydantic AI and the
  OpenAI Agents SDK.
