"""Custom operation handlers for the bank world.

A custom handler has the signature `func(world, clock, **args)` and returns a JSON-serialisable
result. Type the args so worldbench derives the right tool schema (e.g. `amount: float`).
Raise ValueError/LookupError to reject a call — it becomes a clean tool error for the agent.
"""

from __future__ import annotations


def transfer(world, clock, from_id: str, to_id: str, amount: float) -> dict:
    """Move `amount` from one account to another, if the rules allow it, and log it."""
    src = world.accounts.get(from_id)
    dst = world.accounts.get(to_id)
    if src is None or dst is None:
        raise LookupError(f"account {from_id if src is None else to_id} not found")
    if src["status"] != "active":
        raise ValueError(f"account {from_id} is {src['status']}, not active")
    if amount <= 0:
        raise ValueError("amount must be positive")
    if src["balance"] < amount:
        raise ValueError(f"insufficient funds: balance {src['balance']:.2f} < {amount:.2f}")

    world.accounts.update(from_id, balance=round(src["balance"] - amount, 2))
    world.accounts.update(to_id, balance=round(dst["balance"] + amount, 2))
    world.transfers.insert(
        from_id=from_id,
        to_id=to_id,
        amount=amount,
        created_at=clock.now().isoformat() if clock is not None else "",
    )
    return {
        "from_id": from_id,
        "to_id": to_id,
        "amount": amount,
        "from_balance": src["balance"] - amount,
    }
