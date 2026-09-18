# Architecture

Five components. The agent under test never knows it is talking to a fake; it sees MCP tools.

    Agent --MCP--> mcp_server --> faults.injector --> world.engine
                      |
                      +--> trace.recorder
    pytest_plugin ----> engine (assert state), injector (configure), recorder (read trace)

## 1. World engine (`world/`)
- `schema.py`: pydantic models for `world.yaml` (World, Service, RecordType, Field, Operation, SeedSpec).
  Field types: `str`, `int`, `float`, `bool`, `datetime`, `enum[a, b, c]`, `ref[service.record]`.
- `engine.py`: `World.load(path) -> World`. Builds one in-memory `Table` per record type.
  `Table` API: `get(id)`, `all()`, `where(**eq)`, `pick(**eq)` (deterministic first match),
  `insert(record)`, `update(id, **fields)`, `delete(id)`.
  `World` API: `snapshot() -> dict`, `diff(snapshot) -> Diff`, `revision: int` (bumps on every write).
- `seed.py`: faker-based generators per field type, seeded by `world.seed`. CSV/JSON loaders.
- Invariant: same YAML + same seed => identical initial state, byte for byte.

## 2. Fault layer (`faults/`)
- `profile.py`: pydantic models for the `faults:` block. Keyed by `service.operation` or `default`.
  Fields: `latency_ms: [lo, hi]`, `errors: {kind: probability}`, `rate_limit: {calls, per_seconds}`,
  conditional errors (e.g. `not_found_if_newer_than: 2h`).
- `injector.py`: wraps an operation callable. Seeded RNG (`seed + run_index`). Error catalogue:
  `timeout` (actually sleeps past the client deadline), `http_500`, `http_429` (with retry-after),
  `malformed_json`, `empty_result`, `not_found`. Every decision is recorded to the trace.
- `clock.py`: `FakeClock` with `now()`, `advance(seconds)`. The engine and injector read time only from it.
- Invariant: same profile + same seed => identical fault sequence.

## 3. MCP server (`server/`)
- `mcp_server.py`: builds a `mcp.server.Server` from a World + FaultProfile + Recorder.
  One tool per operation, JSON schema derived from the record type. Transports: stdio, streamable HTTP.
- `operations.py`: built-in kinds `get`, `list`, `create`, `update`, `delete`; `custom` resolves
  `handler: "module.func"` and calls `func(world, clock, **args)`.

## 4. Trace (`trace/`)
- `recorder.py`: JSON Lines, one event per tool call:
  `{run, seq, ts, tool, args, fault, latency_ms, ok, result|error, world_rev}`.
- `queries.py`: `Trace.count(tool)`, `calls_to(tool)`, `faults()`, `failures()`.

## 5. pytest plugin (`pytest_plugin.py`)
- Markers: `@pytest.mark.world("path.yaml")`, `@pytest.mark.faults("path.yaml" | dict)`,
  `@pytest.mark.runs(N)`, `@pytest.mark.min_pass_rate(0.9)`.
- Fixtures: `world`, `faults`, `clock`, `mcp_url` (server subprocess per test), `trace`.
- `--runs=N` overrides the marker; report shows `runs / passed / failed / pass rate` and a
  per-failure trace summary. `min_pass_rate` turns the rate into pass/fail for CI.

## Flow of one test
pytest builds World + FaultProfile -> starts MCP server subprocess -> yields `mcp_url`
-> test runs the agent -> test asserts on `world` and `trace` -> server stops, world discarded.
