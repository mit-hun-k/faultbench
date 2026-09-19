"""End-to-end refund demo.

Runs the Pydantic AI agent against a faultbench MCP server generated from
`worlds/shop.yaml` (milestone 3), then prints the final world state and flags any problems.
This is a feel-the-problem script, not a test.

    uv run python examples/shop/demo.py                          # return a delivered order
    uv run python examples/shop/demo.py "return order 5 for me"  # a specific order
    uv run python examples/shop/demo.py --faults                 # turn on shop.yaml's faults

Needs a provider key (copy .env.example to .env and fill it in). Without faults the agent
behaves. With --faults, issue_refund times out 10% of the time (after executing) — run it a
few times and you'll catch the agent refunding a customer twice. Set FAULTBENCH_RUN_INDEX to
walk the deterministic fault sequence.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path

from agent import DEFAULT_WORLD, MODEL, run_agent

from faultbench.world import World

# Which env key each provider prefix needs, so we can fail early with a clear message.
PROVIDER_KEYS = {"openai": "OPENAI_API_KEY", "anthropic": "ANTHROPIC_API_KEY"}


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
    """Report from a world snapshot: {table: {id: row}} (written by the server)."""
    if not state_file.exists():
        print("\n(the agent made no tool calls, so there is no world state to show)")
        return
    snapshot = json.loads(state_file.read_text())
    orders = list(snapshot.get("orders", {}).values())
    refunds = list(snapshot.get("refunds", {}).values())

    print("\n=== final orders ===")
    for order in orders:
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
    by_id = {o["id"]: o for o in orders}
    for rf in refunds:
        status = by_id.get(rf["order_id"], {}).get("status")
        # An order that got a refund should have ended up "returned"; anything else is a leak.
        if status != "returned":
            problems.append(
                f"order {rf['order_id']} was refunded but its status is {status!r}, not 'returned'"
            )
    if not problems:
        print("  none detected in this run (try running it a few times)")
    for p in problems:
        print(f"  ! {p}")


def main() -> int:
    os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")  # keep demo output clean
    load_dotenv()
    provider = MODEL.split(":", 1)[0]
    key = PROVIDER_KEYS.get(provider)
    if key and not os.environ.get(key):
        print(
            f"{key} is not set (needed for model {MODEL!r}). Add it to .env, or set "
            f"FAULTBENCH_DEMO_MODEL to a provider you have a key for."
        )
        return 1

    args = sys.argv[1:]
    faults = "--faults" in args
    run_index = int(os.environ.get("FAULTBENCH_RUN_INDEX", "0"))
    positional = [a for a in args if not a.startswith("-")]

    # Pick a delivered order from the same (deterministic) world the server will build.
    delivered = World.load(DEFAULT_WORLD).orders.pick(status="delivered")
    prompt = (
        positional[0] if positional else f"I want to return order {delivered.id} and get a refund."
    )

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        state_file = Path(tmp.name)
    state_file.unlink(missing_ok=True)  # server creates it on the first tool call

    print(f"prompt: {prompt!r}" + (" [faults ON]" if faults else "") + "\n")
    reply = asyncio.run(
        run_agent(prompt, state_file=str(state_file), faults=faults, run_index=run_index)
    )
    print("=== agent reply ===")
    print(reply)
    report(state_file)
    state_file.unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
