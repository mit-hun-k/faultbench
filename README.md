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

## What it can and can't model
worldbench models services as **flat records** (fields: `str/int/float/bool/datetime/enum/ref`)
with built-in CRUD plus **custom Python operations** for anything else.

- **Fits well:** entities with enums and `ref` relationships; CRUD and list-by-field; business
  rules, state machines, and multi-record writes as custom handlers; array *inputs* via a custom
  op that flattens into a related record type; money as integer minor-units. (See
  [`examples/stripe`](examples/stripe) — a Stripe-style payments API with partial-refund rules.)
- **Caveat:** records are flat — there are **no nested objects or array fields**. Model a
  one-to-many as a related record type + a `ref` (invoice ← line items); a GET returns the
  parent without children inline, so if your agent's correctness depends on a nested *response*
  shape, the fake's shape differs.
- **Not in 0.1:** pagination/cursors, non-equality filters, auth, webhooks, per-request
  idempotency (that last is a bug worldbench helps you *catch*, not prevent). Generated seed
  values are type-correct but not domain-aware — set realistic values in a handler or your test.

## Security
A world file can name Python to import and run (custom handlers, `handler: module.func`), so
loading or serving one executes that code. Only use world files you trust, like any script.

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
