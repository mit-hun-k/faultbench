# shop example

The refund agent demo. Milestone 1 builds `agent.py` and a throwaway dict-backed MCP server;
later milestones replace the server with `worlds/shop.yaml` and add `test_refunds.py`.

Target test (see docs/ARCHITECTURE.md §5):

```python
@pytest.mark.world("worlds/shop.yaml")
@pytest.mark.runs(20)
def test_refund_issued_exactly_once(world, mcp_url, trace):
    order = world.orders.pick(status="delivered")
    run_agent(mcp_url, f"I want to return order {order.id} and get a refund")
    assert len(world.refunds.where(order_id=order.id)) == 1
    assert world.orders.get(order.id).status == "returned"
```
