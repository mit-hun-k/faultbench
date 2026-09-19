# bank example

A second world, to show the format isn't shop-specific. Ten `accounts` and a `transfers`
ledger, with one custom rule: money only moves between the right accounts, with enough funds.

## Files
- `worlds/bank.yaml` — the world. `accounts` (with an `enum` status and a `ref` from
  transfers back to accounts) and a `transfers` ledger; a custom `transfer` operation; and a
  10% timeout on `transfer` so a retry double-moves money.
- `bank_rules.py` — the `transfer` handler: rejects transfers from non-active accounts, for
  non-positive amounts, or beyond the balance; otherwise debits, credits, and logs.

## Serve it

```bash
uv run worldbench serve examples/bank/worlds/bank.yaml            # stdio
uv run worldbench serve examples/bank/worlds/bank.yaml --http     # http://127.0.0.1:8000/mcp
```

## Test it

The bank world is covered by `tests/test_bank_example.py` (no API key needed): it checks the
data is deterministic, that a valid transfer moves both balances and logs a row, that an
over-balance transfer is refused, and that a timeout on `transfer` makes a retry move the
money twice. See `docs/WORLDS.md` to write your own world and `docs/TESTING.md` for the
markers and fixtures.
