# worldbench

**Fake, stateful worlds with fault injection for testing tool-using AI agents.**

Declare your services in a YAML file. worldbench serves them as MCP tools your agent can call,
makes them slow or broken on purpose, records every call, and lets you assert on the world's
end state from pytest, twenty runs at a time.

> Status: pre-alpha, but it works end to end. Write a world, serve it over MCP (stdio or
> HTTP), inject faults, and assert on state from pytest across N seeded runs.
> **Guides:** [write a world](docs/WORLDS.md) · [test an agent](docs/TESTING.md) ·
> examples: [`examples/shop`](examples/shop) (refund agent), [`examples/bank`](examples/bank).
> Validated against **Pydantic AI** and the **OpenAI Agents SDK** (any MCP framework works).

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
from worldbench.integrations.pydantic_ai import run_agent  # or wire any MCP framework


@pytest.mark.world("world.yaml")
@pytest.mark.faults("world.yaml")  # inject the faults: block above
@pytest.mark.runs(20)
@pytest.mark.min_pass_rate(0.95)
async def test_refund_issued_exactly_once(world, mcp_server, trace):
    order = world.orders.pick(status="delivered")
    await run_agent(
        "openai:gpt-5-mini",
        f"Return order {order.id} and refund me",
        mcp=mcp_server,
        system_prompt="You are a refund agent.",
    )
    assert len(world.refunds.where(order_id=order.id)) == 1  # a timeout+retry breaks this
```

```
worldbench: pass rate over runs
test_refund_issued_exactly_once: 17/20 passed (85%)  min_pass_rate=95% -> FAIL
    run4:  get_order → create_return → issue_refund!timeout → issue_refund
    run11: get_order → create_return → issue_refund!timeout → issue_refund
    run18: get_order → create_return → issue_refund!timeout → issue_refund
```

The timeout fired *after* the refund was written, the agent retried, and the customer was
refunded twice — the production bug you couldn't trigger on the real payments API, now a red
test with the trace that explains it.

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
