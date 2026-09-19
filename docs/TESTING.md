# Testing an agent with worldbench

worldbench is a pytest plugin (it loads automatically once installed). You tag a test with
markers, ask for fixtures, run your agent against the served world, and assert on the world's
end state — over many seeded runs, because one pass of a probabilistic agent lies.

## Markers

| Marker | What it does |
| --- | --- |
| `@pytest.mark.world("path.yaml")` | build this world for the test (path is relative to the test file) |
| `@pytest.mark.faults(dict \| "path.yaml")` | apply a fault profile — an inline dict, or a world file's `faults:` block |
| `@pytest.mark.runs(N)` | run the test N times, each a distinct deterministic fault sequence |
| `@pytest.mark.min_pass_rate(r)` | pass CI if the pass rate over the runs is ≥ r (individual run failures are absorbed) |

## Fixtures

| Fixture | What you get |
| --- | --- |
| `world` | the live `World` — assert on it (`world.orders.get(id).status`) |
| `faults` | the resolved `FaultProfile` |
| `clock` | a `FakeClock` you can `advance(seconds)` / `set(when)` |
| `mcp_server` | an **in-process** MCP server sharing the `world` object (fast; assert on `world` directly) |
| `mcp_url` | a server over **HTTP** in a subprocess; use `mcp_url` as the URL and `mcp_url.snapshot()` for end state |
| `trace` | a live `Trace` of every tool call: `count(tool)`, `calls_to(tool)`, `faults()`, `failures()` |

## In-process (recommended)

The `mcp_server` fixture shares the `world` object, so you assert on state directly. With
Pydantic AI, the bundled helper is a one-liner (`pip install 'worldbench[pydantic-ai]'`):

```python
import pytest
from worldbench.integrations.pydantic_ai import run_agent


@pytest.mark.world("worlds/shop.yaml")
@pytest.mark.faults({"payments.issue_refund": {"errors": {"timeout": 0.2}}})
@pytest.mark.runs(20)
@pytest.mark.min_pass_rate(0.9)
async def test_refund_exactly_once(world, mcp_server, trace):
    order = world.orders.pick(status="delivered")
    await run_agent(
        "openai:gpt-5-mini",
        f"Return order {order.id} and refund me",
        mcp=mcp_server,
        system_prompt="You are a refund agent.",
    )
    assert len(world.refunds.where(order_id=order.id)) == 1  # a timeout+retry breaks this
```

`run_agent(model, prompt, mcp=...)` accepts the in-process `mcp_server` or the `mcp_url`
string, so the client side reads the same over both transports. For any other framework, wire
your own agent to `mcp_server` (in-process) or `str(mcp_url)` (HTTP) — it's a standard MCP
server, nothing worldbench-specific.

Run it: `uv run pytest` (or `--runs=50` to override the marker). The summary prints a pass
rate per test and a short trace for each failing run:

```
worldbench: pass rate over runs
tests/test_refund.py::test_refund_exactly_once: 17/20 passed (85%)  min_pass_rate=90% -> FAIL
    run4: get_order → create_return → issue_refund!timeout → issue_refund
```

## Over HTTP (any framework)

For an agent that connects to a URL, use `mcp_url` and assert via its snapshot:

```python
@pytest.mark.world("worlds/shop.yaml")
async def test_over_http(mcp_url):
    run_your_agent(str(mcp_url), "Return order 3 and refund me")  # any MCP-over-HTTP client
    assert mcp_url.snapshot()["orders"]["3"]["status"] == "returned"
```

## Controlling time

`clock` (shared with `mcp_server`) drives time-dependent rules and faults:

```python
@pytest.mark.world("worlds/shop.yaml")
async def test_return_window(world, mcp_server, clock):
    ...
    clock.set(clock.now().replace(year=2030))  # far future -> return window expired
```

## Notes / limits

- **Async tests** (agent runs are async) need `pytest-asyncio`: `pip install pytest-asyncio` and
  set `asyncio_mode = "auto"` under `[tool.pytest.ini_options]` (or `[pytest]` in `pytest.ini`).
  Sync tests that only use `world`/`clock`/`faults` need nothing extra.
- `uv run pytest` needs no API key for the plugin itself; only tests that call a real model do.
  Keep those in an example dir and skip when the key is absent.
- `--runs` is global (applies to every test using `mcp_server`). Combining `@runs` with other
  `@pytest.mark.parametrize` markers on one test isn't supported yet.
- Inline dict faults aren't supported over HTTP (`mcp_url`); use a world file's `faults:` block
  there.
