# stripe example

A realistic world: a Stripe-style payments API, to show how a real backend maps onto
faultbench. Customers, payment intents, charges, refunds, and invoices.

## What it demonstrates
- **Entities + enums + refs + CRUD** declaratively (`currency`, `status`, `reason` enums;
  charges → payment intents → customers via `ref`). Money is `int` minor-units (cents), the
  Stripe way.
- **A state machine and business rules in Python** (`stripe_rules.py`): `confirm_payment_intent`
  moves an intent to `succeeded` and creates a charge; `create_refund` enforces "total refunds
  never exceed the charge" (partial refunds welcome, over-refunds rejected).
- **An array input via a custom op:** `create_invoice(customer_id, lines=[...])` takes a list
  of line items and flattens it into the `invoice_line_items` record type — the pattern for
  one-to-many data (faultbench records are flat; there are no nested/array *fields*).
- **A fault:** `create_refund` times out 10% of the time — the double-refund scenario.

## Try it (keyless)
The flow is covered by `tests/test_stripe_example.py` (no API key): confirm → partial refund
→ remaining → over-refund rejected, and the invoice/line-items array. Serve it for an agent:

```bash
uv run faultbench serve examples/stripe/worlds/stripe.yaml --http
```

See `docs/WORLDS.md` (incl. "What faultbench can and can't model") and `docs/TESTING.md`.
