# shop example

The refund agent demo: a Pydantic AI agent that returns and refunds orders, wired to a
worldbench world so we can test it. As of milestone 3 the MCP server is **generated from**
`worlds/shop.yaml`; the milestone-1 hand-written server is gone.

## Files
- `worlds/shop.yaml` — the world: an `orders` table (50 deterministic fake orders) and a
  `refunds` ledger, with the operations `get_order`, `list_orders`, `create_return`,
  `issue_refund`, and a `faults:` block (used from milestone 4).
- `shop_rules.py` — the `create_return` custom handler: allows a return only for a
  `delivered` order, and (once there's a clock, milestone 4) within a 30-day window.
- `agent.py` — the Pydantic AI refund agent. It spawns `python -m worldbench.server
  worlds/shop.yaml` over stdio and just sees the generated MCP tools. Knows nothing about
  worldbench internals.
- `demo.py` — picks a delivered order, runs one request end to end, then prints the final
  world state and flags problems (double refund, refund of a non-returned order).

## Run it

```bash
cp .env.example .env          # then fill in a provider key
uv run python examples/shop/demo.py
uv run python examples/shop/demo.py "return order 5 for me"   # a specific order
```

Model is `WORLDBENCH_DEMO_MODEL` (default `openai:gpt-5-mini`); set it to e.g.
`anthropic:claude-opus-5` and provide the matching key. You can also serve any world by hand:
`uv run python -m worldbench.server examples/shop/worlds/shop.yaml`.

## What the demo shows (the problem)

`create_return` enforces `delivered`, but `issue_refund` (a plain `create`) has **no
idempotency** — call it twice and you get two refund rows for one order. Yet with gpt-5-mini
and no faults, the agent behaves: on the happy path it does `get_order` → `create_return` →
one `issue_refund`, and asked to refund an already-returned order it *correctly refuses*.

That's the real lesson: **the interesting failures don't reproduce on demand until you
perturb the world.** The double refund needs a *timeout on `issue_refund` that makes the
agent retry* — which is exactly what the fault layer does.

## Faults: the double refund (milestone 4)

`shop.yaml` has a `faults:` block that makes `issue_refund` time out 10% of the time. A
`timeout` fires *after* the refund is written but before the client hears back — so a
retrying agent issues a second refund. Turn it on:

```bash
uv run python examples/shop/demo.py --faults
WORLDBENCH_RUN_INDEX=4 uv run python examples/shop/demo.py --faults   # a run that triggers it
```

Faults are deterministic: same seed + `WORLDBENCH_RUN_INDEX` ⇒ same fault sequence, so a
failure reproduces exactly. Seen live at run_index 4: the agent refunded order 2 twice, and
the demo flagged `order 2 was refunded 2 times (double refund)`.

Still to come: (1) run this as a pytest with the world/faults fixtures (milestone 5), (2) a
trace to assert `issue_refund` ran exactly once, over N seeded runs (milestone 6) — because
one clean pass proves nothing.

Target test (see docs/ARCHITECTURE.md §5):

```python
@pytest.mark.world("worlds/shop.yaml")
@pytest.mark.runs(20)
def test_refund_issued_exactly_once(world, mcp_url, trace):
    order = world.orders.pick(status="delivered")
    run_agent(mcp_url, f"I want to return order {order.id} and get a refund")
    assert len(world.refunds.where(order_id=order.id)) == 1
    assert world.orders.get(order.id).status == "returned"
```
