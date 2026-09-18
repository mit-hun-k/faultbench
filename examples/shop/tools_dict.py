"""Throwaway dict-backed MCP server for the refund demo (worldbench milestone 1).

This is NOT how worldbench works. It is a hand-written stand-in so we can feel the
problem from the agent's side before building the engine. The tools are deliberately
NAIVE: they do no eligibility checks, no return-window check, and no idempotency. If the
agent double-refunds or refunds an ineligible order, the tools let it — that is exactly
what we want to observe. The real fix (guards + fault injection + a trace to assert on)
is what the rest of worldbench builds.

State lives in a plain dict, reset on startup, and mirrored to a JSON file after every
mutation so the demo (a separate process) can inspect the end state and the call log.
The awkwardness of reaching into a subprocess for world state is itself part of the
problem worldbench exists to solve.

Run standalone: `uv run python examples/shop/tools_dict.py` (speaks MCP over stdio).
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

from mcp.server.mcpserver import MCPServer

# --- the "world": five orders and an empty refund ledger --------------------------

ORDERS: dict[str, dict[str, Any]] = {
    "1": {
        "id": "1",
        "customer_id": "cust_a",
        "total": 49.99,
        "status": "delivered",
        "placed_at": "2026-09-05T10:00:00",
    },
    "2": {
        "id": "2",
        "customer_id": "cust_b",
        "total": 120.00,
        "status": "shipped",
        "placed_at": "2026-09-15T14:30:00",
    },
    "3": {
        "id": "3",
        "customer_id": "cust_a",
        "total": 89.50,
        "status": "delivered",
        "placed_at": "2026-09-10T09:15:00",
    },
    "4": {
        "id": "4",
        "customer_id": "cust_c",
        "total": 15.00,
        "status": "placed",
        "placed_at": "2026-09-18T20:00:00",
    },
    "5": {
        "id": "5",
        "customer_id": "cust_b",
        "total": 200.00,
        "status": "returned",
        "placed_at": "2026-08-01T08:00:00",
    },
}

REFUNDS: list[dict[str, Any]] = []
CALLS: list[dict[str, Any]] = []  # a poor-man's trace, so the demo can see what happened

STATE_FILE = Path(os.environ.get("SHOP_STATE_FILE", Path(__file__).with_name(".shop_state.json")))


def _flush() -> None:
    """Mirror the whole world to disk so the out-of-process demo can read end state."""
    STATE_FILE.write_text(
        json.dumps({"orders": ORDERS, "refunds": REFUNDS, "calls": CALLS}, indent=2)
    )


def _log(tool: str, args: dict[str, Any], result: Any) -> None:
    CALLS.append({"tool": tool, "args": args, "result": result})
    print(f"[tools_dict] {tool}({args}) -> {result}", file=sys.stderr)
    _flush()


server = MCPServer("shop-tools", instructions="Refund support tools for the shop demo.")


@server.tool(description="Look up an order by id. Returns the order, or an error if unknown.")
def get_order(order_id: str) -> dict[str, Any]:
    order = ORDERS.get(order_id)
    result = order if order is not None else {"error": f"order {order_id} not found"}
    _log("get_order", {"order_id": order_id}, result)
    return result


@server.tool(description="Mark an order as returned. (Naive: performs no eligibility check.)")
def create_return(order_id: str) -> dict[str, Any]:
    order = ORDERS.get(order_id)
    if order is None:
        result = {"error": f"order {order_id} not found"}
    else:
        order["status"] = "returned"  # no status/window/duplicate guard on purpose
        result = {"order_id": order_id, "status": "returned"}
    _log("create_return", {"order_id": order_id}, result)
    return result


@server.tool(description="Issue a refund for an order. (Naive: no idempotency, no checks.)")
def issue_refund(order_id: str, amount: float) -> dict[str, Any]:
    refund = {"id": f"rf_{len(REFUNDS) + 1}", "order_id": order_id, "amount": amount}
    REFUNDS.append(refund)  # will happily record a second refund for the same order
    _log("issue_refund", {"order_id": order_id, "amount": amount}, refund)
    return refund


if __name__ == "__main__":
    _flush()  # write the clean initial state before any client connects
    server.run("stdio")
