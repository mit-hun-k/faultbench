"""End-to-end refund demo (worldbench milestone 1).

Runs the Pydantic AI agent against the throwaway dict-backed MCP server on a single
request, then prints the final world state and the tool-call log so we can see what the
agent actually did. This is a feel-the-problem script, not a test.

    uv run python examples/shop/demo.py                 # default: return order 3
    uv run python examples/shop/demo.py "refund order 5"

Needs ANTHROPIC_API_KEY (copy .env.example to .env and fill it in).
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path

from agent import run_agent

DEFAULT_PROMPT = "I want to return order 3 and get a refund."


def load_dotenv() -> None:
    """Minimal .env loader (no dependency); does not overwrite existing env vars."""
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


def report(state_file: Path) -> None:
    state = json.loads(state_file.read_text())
    orders, refunds, calls = state["orders"], state["refunds"], state["calls"]

    print("\n=== tool calls ===")
    for i, call in enumerate(calls, 1):
        print(f"{i:>2}. {call['tool']}({call['args']}) -> {call['result']}")

    print("\n=== final orders ===")
    for order in orders.values():
        print(f"  order {order['id']}: {order['status']:<9} ${order['total']:.2f}")

    print("\n=== refunds issued ===")
    if not refunds:
        print("  (none)")
    for rf in refunds:
        print(f"  {rf['id']}: order {rf['order_id']} ${rf['amount']:.2f}")

    print("\n=== problems ===")
    problems = []
    per_order: dict[str, int] = {}
    for rf in refunds:
        per_order[rf["order_id"]] = per_order.get(rf["order_id"], 0) + 1
    for order_id, n in per_order.items():
        if n > 1:
            problems.append(f"order {order_id} was refunded {n} times (double refund)")
    for rf in refunds:
        order = orders.get(rf["order_id"], {})
        # An order eligible for refund must have ended up "returned"; anything else is a leak.
        if order.get("status") != "returned":
            problems.append(
                f"order {rf['order_id']} was refunded but its status is "
                f"{order.get('status', 'unknown')!r}, not 'returned'"
            )
    if not problems:
        print("  none detected in this run (try running it a few times)")
    for p in problems:
        print(f"  ! {p}")


def main() -> int:
    load_dotenv()
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY is not set. Copy .env.example to .env and fill it in.")
        return 1

    prompt = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PROMPT
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        state_file = Path(tmp.name)

    print(f"prompt: {prompt!r}\n")
    reply = asyncio.run(run_agent(prompt, state_file=str(state_file)))
    print("=== agent reply ===")
    print(reply)
    report(state_file)
    state_file.unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
