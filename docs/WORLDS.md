# Writing a world

A world is one YAML file. worldbench loads it into in-memory tables, serves each operation as
an MCP tool, and (optionally) injects faults. Same file + same `seed` ⇒ byte-identical data
every run.

See `examples/shop/worlds/shop.yaml` and `examples/bank/worlds/bank.yaml` for full examples.

## Skeleton

```yaml
name: shop          # required
seed: 42            # optional (default 0); controls the fake data

services:
  orders:                       # a service groups records + operations, and namespaces faults
    records:
      orders:                   # a record type == a table. Names are unique across the world;
        id: str                 #   you reach it as world.orders.
        customer_id: str
        total: float
        status: enum[placed, shipped, delivered, returned]
        placed_at: datetime
    seed:
      count: 50                 # how many rows to generate (default 0 -> empty table)
    operations:
      get_order:   { kind: get,  record: orders }
      list_orders: { kind: list, record: orders, filter: [customer_id] }
      create_return:
        kind: custom
        handler: shop_rules.create_return

faults:                         # optional; see below
  default: { latency_ms: [50, 200] }
```

## Field types

| Type | Meaning |
| --- | --- |
| `str` `int` `float` `bool` | scalars |
| `datetime` | stored as an ISO-8601 string; generated within a recent window |
| `enum[a, b, c]` | one of the listed values |
| `ref[service.record]` | an id pointing at another record type |

A field named `id` is auto-assigned sequential ids (`"1"`, `"2"`, …); don't generate it.

> **YAML gotcha:** write records in **block style** when a field uses `enum[a, b, c]` — the
> commas/brackets break YAML *flow* style (`{ status: enum[a, b, c] }` is a parse error). The
> examples use block style; follow them.

## Operations

Every operation becomes one MCP tool named after the operation. Built-in kinds:

| kind | tool args | does |
| --- | --- | --- |
| `get` | `id` | return one record (error if missing) |
| `list` | the `filter:` fields (all optional) | return matching records |
| `create` | the record's fields (optional; `id` auto-assigned) | insert a record |
| `update` | `id` + fields | update a record |
| `delete` | `id` | delete a record |
| `custom` | from the handler's signature | run your Python |

**Custom handlers** are `handler: "module.func"`, resolved relative to the world file's
directory (and its parent). The function signature is `func(world, clock, **args)`:

```python
def create_return(world, clock, order_id: str) -> dict:
    order = world.orders.get(order_id)
    if order is None:
        raise LookupError(f"order {order_id} not found")
    if order["status"] != "delivered":
        raise ValueError(f"order {order_id} is {order['status']}, not delivered")
    world.orders.update(order_id, status="returned")
    return {"order_id": order_id, "status": "returned"}
```

- **Type the args** (`order_id: str`, `amount: float`) so the tool schema is right.
- **Raise `ValueError`/`LookupError`/`KeyError`** to reject a call — it becomes a clean tool
  error the agent sees, not a server crash.
- Read time only from `clock` (`clock.now()`), never `datetime.now()`, so tests control it.
  `clock` may be `None` when no clock is wired; guard time-dependent checks.

### The world/table API (for handlers and tests)

`world.<record>` is a table: `get(id)`, `all()`, `where(**eq)`, `pick(**eq)` (deterministic
first match), `insert(**fields)`, `update(id, **fields)`, `delete(id)`. Records support both
`row.status` and `row["status"]`. `world.revision` bumps on every write; `world.snapshot()`
and `world.diff(old)` capture state.

## Faults

Keyed by `default` (all operations) or `service.operation`. A rule merges `default` with its
specific entry.

```yaml
faults:
  default:
    latency_ms: [50, 200]                       # sleep a random ms in [lo, hi]
  payments.issue_refund:
    errors: { timeout: 0.10, http_500: 0.02 }   # probabilities (must sum <= 1)
  orders.get_order:
    errors: { not_found_if_newer_than: 2h }      # conditional: a record younger than 2h is "not found"
  # payments.issue_refund:
  #   rate_limit: { calls: 5, per_seconds: 60 }  # 6th call in 60s -> http_429
```

Error kinds: `timeout` (runs the op **then** fails, so a retry double-writes), `http_500`,
`http_429`, `not_found`, `empty_result`, `malformed_json`. `not_found_if_newer_than` and
`rate_limit` are deterministic (driven by the record's timestamp / the clock). Same fault
profile + `seed` + run index ⇒ the same fault sequence.

Durations are `30s`, `2h`, `1d`. Faults are applied in order: latency → conditional not-found
→ rate limit → probabilistic error → run.

## Serving a world

```bash
worldbench serve world.yaml                 # stdio (for a local agent subprocess)
worldbench serve world.yaml --http          # http://127.0.0.1:8000/mcp (any MCP client)
worldbench serve world.yaml --http --faults # also apply the faults: block
```

To test an agent against a world, see `docs/TESTING.md`.
