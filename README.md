# worldbench

**Fake, stateful worlds with fault injection for testing tool-using AI agents.**

Declare your services in a YAML file. worldbench serves them as MCP tools your agent can call,
makes them slow or broken on purpose, records every call, and lets you assert on the world's
end state from pytest, twenty runs at a time.

> Status: pre-alpha, but it works end to end. Write a world, serve it over MCP (stdio or
> HTTP), inject faults, and assert on state from pytest across N seeded runs.
> **Guides:** [write a world](docs/WORLDS.md) · [test an agent](docs/TESTING.md) ·
> examples: [`examples/shop`](examples/shop) (refund agent), [`examples/bank`](examples/bank).

## The problem

Your support agent handles "return my order and refund me." It works when you test by hand.
In production the refund API times out once, the agent retries, and a customer is refunded twice.
You can't make the real payments API time out on command, so you never tested it.

## What it looks like

```yaml
# world.yaml
services:
  orders:
    records: { order: { id: str, status: enum[placed, delivered, returned], total: float } }
    operations: { get_order: { kind: get, record: order } }
  payments:
    records: { refund: { id: str, order_id: str, amount: float } }
    operations: { issue_refund: { kind: create, record: refund } }
faults:
  payments.issue_refund: { errors: { timeout: 0.10 } }
```

```python
@pytest.mark.world("world.yaml")
@pytest.mark.runs(20)
def test_refund_issued_exactly_once(world, mcp_url, trace):
    order = world.orders.pick(status="delivered")
    run_my_agent(mcp_url, f"Return order {order.id} and refund me")
    assert len(world.refunds.where(order_id=order.id)) == 1
```

```
runs: 20   passed: 17   failed: 3   pass rate: 85%
FAILED run 04: expected 1 refund, got 2
  issue_refund -> TIMEOUT (injected)  ->  issue_refund ok  ->  issue_refund ok  <- duplicate
```

## Not in scope
Simulated users, LLM judges, dashboards. Use LangWatch Scenario / DeepEval for users and your own
judge for scoring; worldbench is the environment.

## Quickstart

    uv sync --all-extras
    uv run pytest                                             # the harness test suite (no API key)
    uv run worldbench serve examples/shop/worlds/shop.yaml    # serve a world over MCP (stdio)
    uv run worldbench serve examples/bank/worlds/bank.yaml --http   # ...or over HTTP

Then write your own: [docs/WORLDS.md](docs/WORLDS.md) and [docs/TESTING.md](docs/TESTING.md).

## Development
See `CLAUDE.md` for the session protocol and `docs/` for architecture, decisions and status.

    uv sync --all-extras
    uv run pytest
    uv run pytest examples/shop     # the example agent test (needs a model API key)

## License
Apache 2.0
