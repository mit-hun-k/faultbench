# shop example

The refund agent demo. Milestone 1 (done) is a throwaway, dict-backed MCP server plus a
Pydantic AI agent, wired end to end so we can feel the problem before building the engine.
Later milestones replace the server with `worlds/shop.yaml` and add `test_refunds.py`.

## Files (milestone 1)
- `tools_dict.py` — throwaway MCP server (stdio). Five orders + a refund ledger in a plain
  dict. The three tools (`get_order`, `create_return`, `issue_refund`) are **deliberately
  naive**: no eligibility check, no return-window check, no idempotency. It mirrors its
  state to a JSON file after every call so the out-of-process demo can inspect end state.
- `agent.py` — a Pydantic AI refund-support agent (`anthropic:claude-opus-5`) that connects
  to `tools_dict.py` over stdio. Knows nothing about worldbench; just sees three MCP tools.
- `demo.py` — runs one request end to end, then prints the tool calls, final orders,
  refunds, and any problems it detects (double refund, refund of a non-returned order).
- `shop_rules.py` — the *correct* `create_return` handler. Not wired in until milestone 7;
  kept here as the target behavior the engine will enforce.

## Run it

```bash
cp .env.example .env          # then fill in a provider key
uv run python examples/shop/demo.py
uv run python examples/shop/demo.py "I want to return order 5 and get a refund"  # already returned
```

Model is `WORLDBENCH_DEMO_MODEL` (default `openai:gpt-5-mini`); set it to e.g.
`anthropic:claude-opus-5` and provide the matching key.

## What milestone 1 shows (the problem)

The tools are naive on purpose, so *nothing but the model* stands between a request and a
bad write. Two ways to see it:

- **Keyless**, driving the tools directly: calling `issue_refund` twice records **two**
  refund rows (`rf_1`, `rf_2`) for one order — no idempotency, so a retry double-refunds
  silently. The same tools will also refund order 4 (`placed`, never delivered) or order 5
  (already `returned`) if asked to.
- **Live** (gpt-5-mini): on the happy path it does the right thing — `get_order`,
  `create_return`, one `issue_refund`. Asked to refund the already-returned order 5, it
  looks it up and *correctly refuses*. So a competent model + clean, instant, honest tools
  mostly behaves.

That contrast is the real lesson: **the interesting failures don't reproduce on demand until
you perturb the world.** The double refund needs a *timeout on `issue_refund` that makes the
agent retry*; eligibility bugs need clock skew or stale reads. You also cannot assert on any
of it from the agent side — the world state lives in the server subprocess.

So worldbench needs (1) a world whose end state the test can read, (2) fault injection to
*force* the retry/timeout/skew that triggers the bug, and (3) a trace to assert the tool ran
exactly once — over N seeded runs, because one clean pass proves nothing. Milestones 2–6
build those; then this demo becomes a real, seeded, N-run pytest.

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
