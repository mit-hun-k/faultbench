"""Built-in operation kinds (get, list, create, update, delete) and custom handler resolution.

Milestone 3.

Each built-in maps a record type's CRUD onto a `Table`. `custom` resolves a
`handler: "module.func"` string to a callable and invokes `func(world, clock, **args)`.
Results are plain JSON-serializable dicts/lists so the MCP layer can return them directly.
"""

from __future__ import annotations

import importlib
from collections.abc import Callable
from typing import Any

from ..world import World

BUILTIN_KINDS = frozenset({"get", "list", "create", "update", "delete"})


def resolve_handler(path: str) -> Callable[..., Any]:
    """Turn a "module.func" string into the callable it names."""
    module_name, _, func_name = path.rpartition(".")
    if not module_name:
        raise ValueError(f"handler {path!r} must be of the form 'module.func'")
    module = importlib.import_module(module_name)
    try:
        return getattr(module, func_name)
    except AttributeError as exc:
        raise ValueError(f"handler {path!r}: {func_name!r} not found in {module_name!r}") from exc


def run_builtin(kind: str, world: World, table_name: str, args: dict[str, Any]) -> Any:
    """Execute a built-in CRUD operation and return a JSON-serializable result."""
    table = world.table(table_name)
    if kind == "get":
        rec = table.get(args["id"])
        if rec is None:
            raise ValueError(f"{table_name} {args['id']!r} not found")
        return rec.to_dict()
    if kind == "list":
        filters = {k: v for k, v in args.items() if v is not None}
        return [r.to_dict() for r in table.where(**filters)]
    if kind == "create":
        fields = {k: v for k, v in args.items() if v is not None}
        _check_enums(table, fields)
        return table.insert(**fields).to_dict()
    if kind == "update":
        fields = {k: v for k, v in args.items() if k != "id" and v is not None}
        _check_enums(table, fields)
        return table.update(args["id"], **fields).to_dict()
    if kind == "delete":
        return {"id": str(args["id"]), "deleted": table.delete(args["id"])}
    raise ValueError(f"unknown built-in operation kind {kind!r}")


def _check_enums(table, fields: dict[str, Any]) -> None:
    """Reject writes that set an enum field to a value outside its members."""
    for name, value in fields.items():
        ft = table.record_type.fields.get(name)
        if ft is not None and ft.kind == "enum" and value not in ft.enum_members:
            raise ValueError(f"{name} must be one of {list(ft.enum_members)}, got {value!r}")
