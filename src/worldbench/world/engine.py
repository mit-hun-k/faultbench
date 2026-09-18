"""World and Table: in-memory stateful storage built from a schema. Milestone 2.

`World.load(path)` parses and validates a world file, builds one `Table` per record type,
and seeds it deterministically. Tables are reached on the World by record-type name
(`world.orders`, `world.refunds`); record names are unique across the world so this is
unambiguous. Every write bumps `world.revision`; seeding does not (it is the initial state,
so a freshly loaded world is at revision 0).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .schema import RecordType, WorldSpec, parse_world
from .seed import seed_table

# World attributes a record type must not shadow (since tables are attribute-accessed).
_RESERVED = frozenset(
    {"spec", "name", "seed", "revision", "load", "snapshot", "diff", "table", "tables"}
)


class Record:
    """A single row. Supports both attribute (`row.status`) and item (`row["status"]`)
    access so handlers and tests can use whichever reads best."""

    __slots__ = ("_data",)

    def __init__(self, data: dict[str, Any]) -> None:
        object.__setattr__(self, "_data", dict(data))

    def __getattr__(self, name: str) -> Any:
        try:
            return self._data[name]
        except KeyError:
            raise AttributeError(name) from None

    def __setattr__(self, name: str, value: Any) -> None:
        if name == "_data":
            object.__setattr__(self, name, value)
        else:
            self._data[name] = value

    def __getitem__(self, key: str) -> Any:
        return self._data[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self._data[key] = value

    def __contains__(self, key: str) -> bool:
        return key in self._data

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def to_dict(self) -> dict[str, Any]:
        return dict(self._data)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Record) and self._data == other._data

    def __repr__(self) -> str:
        return f"Record({self._data!r})"


class Table:
    """An ordered collection of rows of one record type."""

    def __init__(self, record_type: RecordType, world: World) -> None:
        self.record_type = record_type
        self._world = world
        self._rows: dict[str, Record] = {}
        self._counter = 0

    # --- reads -------------------------------------------------------------------
    def get(self, id: Any) -> Record | None:
        return self._rows.get(str(id))

    def all(self) -> list[Record]:
        return list(self._rows.values())

    def where(self, **eq: Any) -> list[Record]:
        return [r for r in self._rows.values() if all(r.get(k) == v for k, v in eq.items())]

    def pick(self, **eq: Any) -> Record | None:
        """The first matching row in insertion order (deterministic), or None."""
        for r in self._rows.values():
            if all(r.get(k) == v for k, v in eq.items()):
                return r
        return None

    # --- writes (each bumps world.revision) --------------------------------------
    def insert(self, record: dict[str, Any] | None = None, **fields: Any) -> Record:
        data = dict(record or {})
        data.update(fields)
        if not data.get("id"):
            data["id"] = self._next_id()
        rec = Record(data)
        key = str(rec["id"])
        if key in self._rows:
            raise KeyError(f"{self.record_type.name} id {key!r} already exists")
        self._rows[key] = rec
        self._world._bump()
        return rec

    def update(self, id: Any, **fields: Any) -> Record:
        rec = self._rows.get(str(id))
        if rec is None:
            raise KeyError(f"{self.record_type.name} id {str(id)!r} not found")
        for k, v in fields.items():
            rec[k] = v
        self._world._bump()
        return rec

    def delete(self, id: Any) -> bool:
        if str(id) in self._rows:
            del self._rows[str(id)]
            self._world._bump()
            return True
        return False

    # --- internals ---------------------------------------------------------------
    def _seed_insert(self, data: dict[str, Any]) -> Record:
        rec = Record(data)
        self._rows[str(rec["id"])] = rec
        self._counter += 1
        return rec

    def _next_id(self) -> str:
        self._counter += 1
        # Skip any id an explicit insert already claimed.
        while str(self._counter) in self._rows:
            self._counter += 1
        return str(self._counter)

    def __len__(self) -> int:
        return len(self._rows)

    def __iter__(self):
        return iter(self._rows.values())


@dataclass
class Diff:
    """What changed between two snapshots, keyed by table name."""

    added: dict[str, dict[str, dict]] = field(default_factory=dict)
    removed: dict[str, dict[str, dict]] = field(default_factory=dict)
    changed: dict[str, dict[str, dict[str, tuple]]] = field(default_factory=dict)

    def is_empty(self) -> bool:
        return not (self.added or self.removed or self.changed)

    @classmethod
    def compute(cls, old: dict, new: dict) -> Diff:
        d = cls()
        for table in set(old) | set(new):
            o, n = old.get(table, {}), new.get(table, {})
            for rid in n.keys() - o.keys():
                d.added.setdefault(table, {})[rid] = n[rid]
            for rid in o.keys() - n.keys():
                d.removed.setdefault(table, {})[rid] = o[rid]
            for rid in o.keys() & n.keys():
                if o[rid] != n[rid]:
                    fields = set(o[rid]) | set(n[rid])
                    delta = {
                        k: (o[rid].get(k), n[rid].get(k))
                        for k in fields
                        if o[rid].get(k) != n[rid].get(k)
                    }
                    d.changed.setdefault(table, {})[rid] = delta
        return d


class World:
    """A live, stateful world: a set of named tables plus a monotonic revision."""

    def __init__(self, spec: WorldSpec) -> None:
        self.spec = spec
        self.name = spec.name
        self.seed = spec.seed
        self.revision = 0
        self._tables: dict[str, Table] = {}
        for service in spec.services.values():
            for rname, rtype in service.records.items():
                if rname in _RESERVED:
                    raise ValueError(
                        f"record name {rname!r} collides with a reserved World attribute"
                    )
                self._tables[rname] = Table(rtype, self)

    @classmethod
    def load(cls, path: str | Path) -> World:
        data = yaml.safe_load(Path(path).read_text())
        world = cls(parse_world(data))
        world._seed()
        return world

    def table(self, name: str) -> Table:
        return self._tables[name]

    def snapshot(self) -> dict[str, dict[str, dict]]:
        return {
            name: {rid: rec.to_dict() for rid, rec in t._rows.items()}
            for name, t in self._tables.items()
        }

    def diff(self, old: dict) -> Diff:
        return Diff.compute(old, self.snapshot())

    def _seed(self) -> None:
        for service in self.spec.services.values():
            count = service.seed.count if service.seed else 0
            for rname, rtype in service.records.items():
                seed_table(self._tables[rname], rtype, count, self)

    def _bump(self) -> None:
        self.revision += 1

    def __getattr__(self, name: str) -> Table:
        # Only reached when normal attribute lookup fails, so real attributes win.
        tables = self.__dict__.get("_tables", {})
        if name in tables:
            return tables[name]
        raise AttributeError(name)
