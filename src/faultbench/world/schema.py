"""Pydantic models for world.yaml. Milestone 2. See docs/ARCHITECTURE.md §1.

These are the parsed, validated *schema* of a world file. The runtime, stateful world
(tables you can read and write) lives in engine.py as `World`; to avoid two classes named
`World`, the schema root here is `WorldSpec`.

Field types are written as strings in YAML and parsed by `FieldType.parse`:
    str  int  float  bool  datetime
    enum[a, b, c]        -> kind="enum", enum_members=("a", "b", "c")
    ref[service.record]  -> kind="ref",  ref_target="service.record"
"""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, model_validator

SCALAR_KINDS = frozenset({"str", "int", "float", "bool", "datetime"})
_ENUM_RE = re.compile(r"^enum\[(.*)\]$")
_REF_RE = re.compile(r"^ref\[([\w.]+)\]$")

FieldKind = Literal["str", "int", "float", "bool", "datetime", "enum", "ref"]


class FieldType(BaseModel):
    """A single field's type, parsed from its YAML string form."""

    raw: str
    kind: FieldKind
    enum_members: tuple[str, ...] | None = None
    ref_target: str | None = None  # "service.record" as written in the YAML

    @classmethod
    def parse(cls, raw: str) -> FieldType:
        raw = raw.strip()
        if raw in SCALAR_KINDS:
            return cls(raw=raw, kind=raw)  # type: ignore[arg-type]
        if m := _ENUM_RE.match(raw):
            members = tuple(x.strip() for x in m.group(1).split(",") if x.strip())
            if not members:
                raise ValueError(f"enum type has no members: {raw!r}")
            return cls(raw=raw, kind="enum", enum_members=members)
        if m := _REF_RE.match(raw):
            return cls(raw=raw, kind="ref", ref_target=m.group(1))
        raise ValueError(
            f"unknown field type: {raw!r} "
            f"(expected one of {sorted(SCALAR_KINDS)}, enum[...], or ref[service.record])"
        )

    @property
    def ref_record(self) -> str | None:
        """The record name a ref points at (the part after the dot)."""
        return self.ref_target.split(".")[-1] if self.ref_target else None


class RecordType(BaseModel):
    name: str
    fields: dict[str, FieldType]


class SeedSpec(BaseModel):
    count: int = 0


class OperationSpec(BaseModel):
    name: str
    kind: Literal["get", "list", "create", "update", "delete", "custom"]
    record: str | None = None
    filter: list[str] | None = None
    handler: str | None = None

    @model_validator(mode="after")
    def _check(self) -> OperationSpec:
        if self.kind == "custom":
            if not self.handler:
                raise ValueError(f"custom operation {self.name!r} needs a handler")
        elif not self.record:
            raise ValueError(f"operation {self.name!r} ({self.kind}) needs a record")
        return self


class ServiceSpec(BaseModel):
    name: str
    records: dict[str, RecordType]
    seed: SeedSpec | None = None
    operations: dict[str, OperationSpec] = {}


class WorldSpec(BaseModel):
    name: str
    seed: int = 0
    services: dict[str, ServiceSpec]

    @model_validator(mode="after")
    def _validate_refs_and_names(self) -> WorldSpec:
        # Record names are the accessor on the runtime World (world.orders), so they must be
        # unique across the whole world, not just within a service.
        owner: dict[str, str] = {}
        for service in self.services.values():
            for rname in service.records:
                if rname in owner:
                    raise ValueError(
                        f"record name {rname!r} is defined in both services "
                        f"{owner[rname]!r} and {service.name!r}; record names must be "
                        f"unique across the world"
                    )
                owner[rname] = service.name
        for service in self.services.values():
            for record in service.records.values():
                for fname, ft in record.fields.items():
                    if ft.kind == "ref" and ft.ref_record not in owner:
                        raise ValueError(
                            f"{record.name}.{fname} references unknown record {ft.ref_target!r}"
                        )
            for op in service.operations.values():
                if op.record and op.record not in service.records:
                    raise ValueError(
                        f"operation {op.name!r} references unknown record "
                        f"{op.record!r} in service {service.name!r}"
                    )
        return self


def parse_world(data: dict) -> WorldSpec:
    """Build a validated WorldSpec from a raw parsed-YAML dict."""
    if "name" not in data:
        raise ValueError("world file needs a top-level 'name'")
    services_raw = data.get("services") or {}
    if not isinstance(services_raw, dict):
        raise ValueError("'services' must be a mapping of service name -> service")
    services: dict[str, ServiceSpec] = {}
    for sname, sbody in services_raw.items():
        if not isinstance(sbody, dict):
            raise ValueError(f"service {sname!r} must be a mapping")
        records_raw = sbody.get("records") or {}
        if not isinstance(records_raw, dict):
            raise ValueError(f"service {sname!r}: 'records' must be a mapping")
        records: dict[str, RecordType] = {}
        for rname, rfields in records_raw.items():
            if not isinstance(rfields, dict):
                raise ValueError(f"record {rname!r} must be a mapping of field -> type")
            try:
                fields = {fn: FieldType.parse(ft) for fn, ft in rfields.items()}
            except ValueError as exc:
                raise ValueError(f"record {rname!r}: {exc}") from exc
            records[rname] = RecordType(name=rname, fields=fields)
        seed = SeedSpec(**sbody["seed"]) if "seed" in sbody else None
        operations = {
            on: OperationSpec(name=on, **ob) for on, ob in (sbody.get("operations") or {}).items()
        }
        services[sname] = ServiceSpec(name=sname, records=records, seed=seed, operations=operations)
    return WorldSpec(name=data["name"], seed=data.get("seed", 0), services=services)
