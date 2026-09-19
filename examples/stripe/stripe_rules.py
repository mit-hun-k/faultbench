"""Custom handlers for the Stripe-style world."""


def _now(clock):
    return clock.now().isoformat() if clock is not None else ""


def confirm_payment_intent(world, clock, payment_intent_id: str) -> dict:
    pi = world.payment_intents.get(payment_intent_id)
    if pi is None:
        raise LookupError(f"payment_intent {payment_intent_id} not found")
    if pi["status"] != "requires_confirmation":
        raise ValueError(f"payment_intent is {pi['status']}, not confirmable")
    world.payment_intents.update(payment_intent_id, status="succeeded")
    charge = world.charges.insert(
        payment_intent_id=payment_intent_id,
        amount=pi["amount"],
        status="succeeded",
        created=_now(clock),
    )
    return {
        "payment_intent_id": payment_intent_id,
        "charge_id": charge["id"],
        "status": "succeeded",
    }


def create_refund(
    world, clock, charge_id: str, amount: int | None = None, reason: str = "requested_by_customer"
) -> dict:
    charge = world.charges.get(charge_id)
    if charge is None:
        raise LookupError(f"charge {charge_id} not found")
    if charge["status"] != "succeeded":
        raise ValueError(f"charge {charge_id} is {charge['status']}, not succeeded")
    already = sum(r["amount"] for r in world.refunds.where(charge_id=charge_id))
    amt = charge["amount"] - already if amount is None else amount
    if amt <= 0:
        raise ValueError("nothing left to refund")
    if already + amt > charge["amount"]:
        raise ValueError(f"refund exceeds charge: {already}+{amt} > {charge['amount']}")
    refund = world.refunds.insert(
        charge_id=charge_id,
        amount=amt,
        reason=reason,
        status="succeeded",
        created=_now(clock),
    )
    return refund.to_dict()


def create_invoice(world, clock, customer_id: str, lines: list) -> dict:
    """Stripe invoices carry a LIST of line items. faultbench has no list/nested field, so we
    take the array as a custom-op arg and flatten it into a related record type."""
    total = sum(li["amount"] * li.get("quantity", 1) for li in lines)
    inv = world.invoices.insert(
        customer_id=customer_id,
        total=total,
        status="open",
        created=_now(clock),
    )
    for li in lines:
        world.invoice_line_items.insert(
            invoice_id=inv["id"],
            description=li["description"],
            amount=li["amount"],
            quantity=li.get("quantity", 1),
        )
    return {"invoice_id": inv["id"], "total": total, "line_count": len(lines)}
