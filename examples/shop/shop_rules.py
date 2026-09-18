"""Custom operation handlers for the shop world. Wired in at milestone 7."""

from datetime import timedelta

RETURN_WINDOW = timedelta(days=30)


def create_return(world, clock, order_id: str) -> dict:
    """Create a return only if the order is delivered and within the return window."""
    order = world.orders.get(order_id)
    if order is None:
        raise LookupError(f"order {order_id} not found")
    if order["status"] != "delivered":
        raise ValueError(f"order {order_id} is {order['status']}, not delivered")
    if clock.now() - order["placed_at"] > RETURN_WINDOW:
        raise ValueError(f"order {order_id} is outside the {RETURN_WINDOW.days}-day return window")
    world.orders.update(order_id, status="returned")
    return {"order_id": order_id, "status": "returned"}
