"""Validates the Stripe-style example world keylessly (no model key), via the documented
in-process pattern. Also exercises the array-input (invoice line items) modeling pattern."""

import pytest

WORLD = "../examples/stripe/worlds/stripe.yaml"  # relative to this test file


@pytest.mark.world(WORLD)
async def test_payment_confirm_and_partial_refunds(world, mcp_server):
    cust = world.customers.all()[0]
    await mcp_server.call_tool(
        "create_payment_intent",
        {
            "customer_id": cust.id,
            "amount": 2000,
            "currency": "usd",
            "status": "requires_confirmation",
        },
    )
    pi = world.payment_intents.all()[-1]
    await mcp_server.call_tool("confirm_payment_intent", {"payment_intent_id": pi.id})
    charge = world.charges.all()[-1]
    assert charge.status == "succeeded"

    await mcp_server.call_tool("create_refund", {"charge_id": charge.id, "amount": 500})
    await mcp_server.call_tool("create_refund", {"charge_id": charge.id})  # remaining
    assert sum(r.amount for r in world.refunds.where(charge_id=charge.id)) == 2000

    with pytest.raises(Exception, match="exceeds"):
        await mcp_server.call_tool("create_refund", {"charge_id": charge.id, "amount": 1})


@pytest.mark.world(WORLD)
async def test_invoice_array_is_flattened(world, mcp_server):
    cust = world.customers.all()[0]
    lines = [
        {"description": "Seat", "amount": 1000, "quantity": 2},
        {"description": "Setup fee", "amount": 500, "quantity": 1},
    ]
    await mcp_server.call_tool("create_invoice", {"customer_id": cust.id, "lines": lines})
    inv = world.invoices.all()[-1]
    assert inv.total == 2500
    assert len(world.invoice_line_items.where(invoice_id=inv.id)) == 2


@pytest.mark.world(WORLD)
async def test_bad_enum_is_rejected(world, mcp_server):
    cust = world.customers.all()[0]
    # An invalid enum is rejected — here at the MCP schema layer (the enum is a Literal), so the
    # bad value never reaches the world.
    with pytest.raises(Exception, match="currency"):
        await mcp_server.call_tool(
            "create_payment_intent",
            {
                "customer_id": cust.id,
                "amount": 100,
                "currency": "xyz",
                "status": "requires_confirmation",
            },
        )
    assert not [pi for pi in world.payment_intents.all() if pi.get("currency") == "xyz"]
