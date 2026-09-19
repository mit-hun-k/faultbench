"""MCP server generation tests (milestone 3).

Proves the toy agent's three tools work against a server generated from shop.yaml, using an
in-memory MCP client (no subprocess, no model, no API key). Also unit-tests the operation
layer directly.
"""

import json
from pathlib import Path

import pytest
from pydantic_ai.mcp import FastMCPClient

from faultbench.server import build_server, resolve_handler, run_builtin
from faultbench.world import World

SHOP = Path(__file__).resolve().parents[1] / "examples/shop/worlds/shop.yaml"


@pytest.fixture
def world():
    return World.load(SHOP)


def content_json(result):
    """Extract the JSON payload from an (unstructured) tool result."""
    return json.loads(result.content[0].text)


# --- tool generation ------------------------------------------------------------


async def test_tools_and_schemas(world):
    async with FastMCPClient(build_server(world)) as client:
        tools = {t.name: t for t in await client.list_tools()}
        assert set(tools) == {"get_order", "list_orders", "create_return", "issue_refund"}
        assert list(tools["get_order"].input_schema["properties"]) == ["id"]
        assert set(tools["issue_refund"].input_schema["properties"]) == {
            "order_id",
            "amount",
            "created_at",
        }
        # order_id comes from the custom handler's signature and is required
        assert tools["create_return"].input_schema["properties"]["order_id"]["type"] == "string"


async def test_get_order_returns_row(world):
    async with FastMCPClient(build_server(world)) as client:
        result = await client.call_tool("get_order", {"id": "1"})
        assert content_json(result) == world.orders.get("1").to_dict()


async def test_refund_flow_updates_world(world):
    order = world.orders.pick(status="delivered")
    async with FastMCPClient(build_server(world)) as client:
        await client.call_tool("get_order", {"id": order.id})
        await client.call_tool("create_return", {"order_id": order.id})
        await client.call_tool("issue_refund", {"order_id": order.id, "amount": order.total})
    # The in-memory server shares this World object, so we can assert on it directly.
    assert world.orders.get(order.id).status == "returned"
    assert len(world.refunds.where(order_id=order.id)) == 1


async def test_list_orders_filters(world):
    some = world.orders.all()[0]
    async with FastMCPClient(build_server(world)) as client:
        result = await client.call_tool("list_orders", {"customer_id": some.customer_id})
    rows = [json.loads(c.text) for c in result.content]  # one content block per row
    assert rows  # at least the one we know about
    assert all(r["customer_id"] == some.customer_id for r in rows)


# --- business errors surface as clean tool errors -------------------------------


async def test_missing_order_is_tool_error(world):
    async with FastMCPClient(build_server(world)) as client:
        with pytest.raises(Exception, match="not found"):
            await client.call_tool("get_order", {"id": "999"})


async def test_return_non_delivered_is_tool_error(world):
    placed = world.orders.pick(status="placed")
    async with FastMCPClient(build_server(world)) as client:
        with pytest.raises(Exception, match="not delivered"):
            await client.call_tool("create_return", {"order_id": placed.id})


# --- operation layer (direct, no MCP) -------------------------------------------


def test_run_builtin_crud(world):
    assert run_builtin("get", world, "orders", {"id": "1"})["id"] == "1"
    listed = run_builtin(
        "list", world, "orders", {"customer_id": world.orders.get("1").customer_id}
    )
    assert isinstance(listed, list) and listed
    created = run_builtin("create", world, "refunds", {"order_id": "1", "amount": 5.0})
    assert created["order_id"] == "1"
    updated = run_builtin("update", world, "orders", {"id": "1", "status": "returned"})
    assert updated["status"] == "returned"
    deleted = run_builtin("delete", world, "orders", {"id": "1"})
    assert deleted == {"id": "1", "deleted": True}


def test_run_builtin_get_missing_raises(world):
    with pytest.raises(ValueError, match="not found"):
        run_builtin("get", world, "orders", {"id": "nope"})


def test_run_builtin_rejects_bad_enum(world):
    with pytest.raises(ValueError, match="must be one of"):
        run_builtin("update", world, "orders", {"id": "1", "status": "banana"})
    # a valid enum value is accepted
    assert (
        run_builtin("update", world, "orders", {"id": "1", "status": "returned"})["status"]
        == "returned"
    )


async def test_enum_param_advertises_its_values():
    mini = World.load(Path(__file__).parent / "worlds/mini.yaml")
    async with FastMCPClient(build_server(mini)) as client:
        tools = {t.name: t for t in await client.list_tools()}
        status = tools["sell_widget"].input_schema["properties"]["status"]
    text = json.dumps(status)
    assert '"new"' in text and '"sold"' in text  # the enum members are in the schema


def test_resolve_handler_ok_and_errors():
    fn = resolve_handler("faultbench.server.operations.run_builtin")
    assert callable(fn)
    with pytest.raises(ValueError, match="module.func"):
        resolve_handler("nomodule")
    with pytest.raises(ValueError, match="not found"):
        resolve_handler("faultbench.server.operations.does_not_exist")
