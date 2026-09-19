"""Unit tests for the world engine (milestone 2): schema parsing, deterministic seeding,
Table CRUD, revision, snapshot/diff."""

from datetime import datetime
from pathlib import Path

import pytest

from faultbench.world import FieldType, World, parse_world
from faultbench.world.seed import load_rows

SHOP = Path(__file__).resolve().parents[1] / "examples/shop/worlds/shop.yaml"


def write_world(tmp_path, seed=1, count=5, extra_services=""):
    text = f"""
name: tiny
seed: {seed}
services:
  people:
    records:
      people:
        id: str
        name: str
        age: int
        active: bool
        score: float
        role: enum[admin, user, guest]
        born: datetime
    seed:
      count: {count}
    operations:
      get_person: {{ kind: get, record: people }}
{extra_services}
"""
    p = tmp_path / "tiny.yaml"
    p.write_text(text)
    return p


# --- field type parsing ---------------------------------------------------------


@pytest.mark.parametrize("raw", ["str", "int", "float", "bool", "datetime"])
def test_scalar_field_types(raw):
    assert FieldType.parse(raw).kind == raw


def test_enum_field_type():
    ft = FieldType.parse("enum[a, b, c]")
    assert ft.kind == "enum"
    assert ft.enum_members == ("a", "b", "c")


def test_ref_field_type():
    ft = FieldType.parse("ref[orders.orders]")
    assert ft.kind == "ref"
    assert ft.ref_target == "orders.orders"
    assert ft.ref_record == "orders"


def test_unknown_field_type_raises():
    with pytest.raises(ValueError, match="unknown field type"):
        FieldType.parse("blob")


def test_empty_enum_raises():
    with pytest.raises(ValueError, match="no members"):
        FieldType.parse("enum[]")


# --- schema validation ----------------------------------------------------------


def test_duplicate_record_name_across_services_raises():
    data = {
        "name": "dup",
        "services": {
            "a": {"records": {"thing": {"id": "str"}}},
            "b": {"records": {"thing": {"id": "str"}}},
        },
    }
    with pytest.raises(ValueError, match="unique across the world"):
        parse_world(data)


def test_custom_op_without_handler_raises():
    data = {
        "name": "w",
        "services": {
            "s": {"records": {"r": {"id": "str"}}, "operations": {"o": {"kind": "custom"}}}
        },
    }
    with pytest.raises(ValueError, match="needs a handler"):
        parse_world(data)


def test_op_with_unknown_record_raises():
    data = {
        "name": "w",
        "services": {
            "s": {
                "records": {"r": {"id": "str"}},
                "operations": {"o": {"kind": "get", "record": "nope"}},
            }
        },
    }
    with pytest.raises(ValueError, match="unknown record"):
        parse_world(data)


def test_ref_to_unknown_record_raises():
    data = {"name": "w", "services": {"s": {"records": {"r": {"id": "str", "x": "ref[s.ghost]"}}}}}
    with pytest.raises(ValueError, match="unknown record"):
        parse_world(data)


# --- loading shop.yaml ----------------------------------------------------------


def test_load_shop():
    world = World.load(SHOP)
    assert world.name == "shop"
    assert world.seed == 42
    assert len(world.orders) == 50
    assert len(world.refunds) == 0
    assert world.revision == 0  # seeding does not count as a write


def test_shop_ids_are_sequential_strings():
    world = World.load(SHOP)
    assert [o.id for o in world.orders.all()] == [str(i) for i in range(1, 51)]


def test_shop_enum_and_datetime_values_are_valid():
    world = World.load(SHOP)
    allowed = {"placed", "shipped", "delivered", "returned"}
    for o in world.orders.all():
        assert o.status in allowed
        datetime.fromisoformat(o.placed_at)  # parses => valid ISO string


# --- determinism (the core invariant) -------------------------------------------


def test_same_seed_is_byte_identical(tmp_path):
    p = write_world(tmp_path, seed=7)
    assert World.load(p).snapshot() == World.load(p).snapshot()


def test_different_seed_differs(tmp_path):
    da, db = tmp_path / "a", tmp_path / "b"
    da.mkdir()
    db.mkdir()
    a = World.load(write_world(da, seed=1))
    b = World.load(write_world(db, seed=2))
    assert a.snapshot() != b.snapshot()


def test_shop_load_is_deterministic():
    assert World.load(SHOP).snapshot() == World.load(SHOP).snapshot()


# --- table reads ----------------------------------------------------------------


def test_pick_is_deterministic_first_match():
    world = World.load(SHOP)
    first = world.orders.pick(status="delivered")
    assert first is not None
    # pick returns the earliest matching row in insertion order
    delivered = [o for o in world.orders.all() if o.status == "delivered"]
    assert first.id == delivered[0].id


def test_where_returns_all_matches():
    world = World.load(SHOP)
    delivered = world.orders.where(status="delivered")
    assert len(delivered) == sum(o.status == "delivered" for o in world.orders.all())


def test_get_by_id_and_missing():
    world = World.load(SHOP)
    assert world.orders.get("1").id == "1"
    assert world.orders.get("999") is None


def test_record_dual_access():
    world = World.load(SHOP)
    o = world.orders.get("1")
    assert o.id == o["id"]
    assert "status" in o
    assert o.get("missing", "d") == "d"


# --- table writes + revision ----------------------------------------------------


def test_insert_bumps_revision_and_autoassigns_id():
    world = World.load(SHOP)
    before = world.revision
    r = world.refunds.insert(order_id="1", amount=10.0, created_at="2020-01-01T00:00:00")
    assert r.id == "1"
    assert len(world.refunds) == 1
    assert world.revision == before + 1


def test_update_changes_field_and_bumps_revision():
    world = World.load(SHOP)
    before = world.revision
    world.orders.update("1", status="returned")
    assert world.orders.get("1").status == "returned"
    assert world.revision == before + 1


def test_update_missing_raises():
    world = World.load(SHOP)
    with pytest.raises(KeyError):
        world.orders.update("999", status="returned")


def test_delete_removes_and_bumps_revision():
    world = World.load(SHOP)
    before = world.revision
    assert world.orders.delete("1") is True
    assert world.orders.get("1") is None
    assert world.revision == before + 1
    assert world.orders.delete("1") is False  # already gone, no bump
    assert world.revision == before + 1


def test_insert_duplicate_id_raises():
    world = World.load(SHOP)
    with pytest.raises(KeyError, match="already exists"):
        world.orders.insert(id="1")


# --- snapshot / diff ------------------------------------------------------------


def test_diff_detects_change_and_add():
    world = World.load(SHOP)
    snap = world.snapshot()
    world.orders.update("1", status="returned")
    world.refunds.insert(order_id="1", amount=5.0, created_at="2020-01-01T00:00:00")
    diff = world.diff(snap)
    assert diff.changed["orders"]["1"]["status"][1] == "returned"
    assert "1" in diff.added["refunds"]


def test_diff_empty_when_unchanged():
    world = World.load(SHOP)
    assert world.diff(world.snapshot()).is_empty()


# --- ref seeding ----------------------------------------------------------------


def test_ref_values_point_at_existing_rows(tmp_path):
    extra = """
  payments:
    records:
      payments:
        id: str
        person_id: ref[people.people]
    seed:
      count: 4
"""
    world = World.load(write_world(tmp_path, seed=3, count=6, extra_services=extra))
    person_ids = {p.id for p in world.people.all()}
    assert len(world.payments) == 4
    for pay in world.payments.all():
        assert pay.person_id in person_ids


# --- seed file loaders ----------------------------------------------------------


def test_load_rows_json(tmp_path):
    p = tmp_path / "rows.json"
    p.write_text('[{"id": "1", "name": "a"}]')
    assert load_rows(p) == [{"id": "1", "name": "a"}]


def test_load_rows_csv(tmp_path):
    p = tmp_path / "rows.csv"
    p.write_text("id,name\n1,a\n2,b\n")
    rows = load_rows(p)
    assert rows == [{"id": "1", "name": "a"}, {"id": "2", "name": "b"}]
