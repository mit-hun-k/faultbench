"""Build an MCP server from a World. Milestones 3–4.

`build_server(world)` registers one MCP tool per declared operation. Each tool's input
schema is derived from the record type (or, for `custom`, from the handler's signature) by
giving a wrapper function an explicit `__signature__`, which the mcp SDK turns into a JSON
schema. Tools return the world's own dicts/lists.

If `faults` is given, every call goes through a seeded Injector (latency + errors). A
`timeout` fault runs the op and then fails, so a retrying client double-writes; the injected
error is surfaced as a ToolError. Custom handlers are called as `handler(world, clock,
**args)`; `clock` is None unless one is passed (the return-window check stays off until then).
"""

from __future__ import annotations

import inspect
import json
import sys
from pathlib import Path
from typing import Any

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from ..faults import FakeClock, FaultError, FaultProfile, FaultTimeout, Injector
from ..trace import Recorder
from ..world import OperationSpec, World
from .operations import resolve_handler, run_builtin

# Exceptions a handler/operation raises to reject a call for a business reason (not a bug).
# These become clean MCP tool errors the agent can read, rather than server crashes.
_BUSINESS_ERRORS = (ValueError, LookupError, KeyError)

# Field kind -> the Python type advertised in the tool's JSON schema.
_PYTYPE: dict[str, type] = {
    "str": str,
    "int": int,
    "float": float,
    "bool": bool,
    "datetime": str,
    "enum": str,
    "ref": str,
}
_EMPTY = inspect.Parameter.empty


def build_server(
    world: World,
    clock: Any = None,
    state_file: str | None = None,
    faults: FaultProfile | None = None,
    run_index: int = 0,
    recorder: Recorder | None = None,
) -> MCPServer:
    """Create an MCPServer exposing one tool per operation in `world`.

    If `faults` is given, every tool call goes through a seeded Injector (latency + errors).
    If `recorder` is given, every call is recorded to the trace.
    """
    _ensure_handler_path(world)
    injector = (
        Injector(faults, seed=world.seed, run_index=run_index, clock=clock)
        if faults and not faults.is_empty()
        else None
    )
    server = MCPServer(world.name, instructions=f"Generated tools for the {world.name} world.")
    for service in world.spec.services.values():
        for op in service.operations.values():
            fn = _make_tool_fn(world, clock, service.name, op, state_file, injector, recorder)
            server.add_tool(
                fn,
                name=op.name,
                description=_describe(op),
                structured_output=False,
            )
    return server


def serve_stdio(
    world_path: str | Path,
    clock: Any = None,
    state_file: str | None = None,
    faults: FaultProfile | None = None,
    run_index: int = 0,
) -> None:
    """Load a world file and serve it over stdio (blocking). Uses a FakeClock at its default
    'now' unless one is given, so time-dependent rules (return window, sync lag) are active."""
    world = World.load(world_path)
    if clock is None:
        clock = FakeClock()
    build_server(world, clock=clock, state_file=state_file, faults=faults, run_index=run_index).run(
        "stdio"
    )


def serve_http(
    world_path: str | Path,
    host: str = "127.0.0.1",
    port: int = 8000,
    path: str = "/mcp",
    clock: Any = None,
    state_file: str | None = None,
    faults: FaultProfile | None = None,
    run_index: int = 0,
) -> None:
    """Load a world file and serve it over streamable HTTP at http://host:port{path} (blocking).

    The served world runs in its own process, so it does NOT share the in-process `world`
    object; a client asserts on end state via the state file (see WORLDBENCH_STATE_FILE)."""
    world = World.load(world_path)
    if clock is None:
        clock = FakeClock()
    build_server(world, clock=clock, state_file=state_file, faults=faults, run_index=run_index).run(
        "streamable-http", host=host, port=port, streamable_http_path=path
    )


# --- internals ------------------------------------------------------------------


def _describe(op: OperationSpec) -> str:
    if op.kind == "custom":
        return f"{op.name} (custom handler {op.handler})"
    return f"{op.name}: {op.kind} on {op.record}"


def _ensure_handler_path(world: World) -> None:
    """Put the world file's directory and its parent on sys.path so custom handler
    modules (e.g. shop_rules) import by their bare name."""
    if not world.source_path:
        return
    base = world.source_path.resolve().parent
    for path in (base, base.parent):
        p = str(path)
        if p not in sys.path:
            sys.path.insert(0, p)


def _params_for(world: World, op: OperationSpec, clock: Any) -> list[inspect.Parameter]:
    """The parameters a tool exposes, in schema order."""

    def param(name: str, pytype: type, required: bool) -> inspect.Parameter:
        return inspect.Parameter(
            name,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            annotation=pytype,
            default=_EMPTY if required else None,
        )

    if op.kind == "custom":
        handler = resolve_handler(op.handler)
        params = []
        for name, sp in inspect.signature(handler).parameters.items():
            if name in ("world", "clock"):
                continue
            ann = sp.annotation if sp.annotation is not _EMPTY else str
            required = sp.default is inspect.Parameter.empty
            params.append(param(name, ann, required))
        return params

    fields = world.table(op.record).record_type.fields
    if op.kind in ("get", "delete"):
        return [param("id", _PYTYPE[fields["id"].kind], True)]
    if op.kind == "update":
        out = [param("id", _PYTYPE[fields["id"].kind], True)]
        out += [param(n, _PYTYPE[ft.kind], False) for n, ft in fields.items() if n != "id"]
        return out
    if op.kind == "create":
        return [param(n, _PYTYPE[ft.kind], False) for n, ft in fields.items() if n != "id"]
    if op.kind == "list":
        names = op.filter or []
        return [param(n, _PYTYPE[fields[n].kind], False) for n in names]
    raise ValueError(f"unsupported operation kind {op.kind!r}")


def _make_tool_fn(
    world: World,
    clock: Any,
    service_name: str,
    op: OperationSpec,
    state_file: str | None,
    injector: Injector | None,
    recorder: Recorder | None,
):
    params = _params_for(world, op, clock)
    handler = resolve_handler(op.handler) if op.kind == "custom" else None

    def do(kwargs: dict[str, Any]) -> Any:
        try:
            if op.kind == "custom":
                return handler(world, clock, **kwargs)
            return run_builtin(op.kind, world, op.record, dict(kwargs))
        except _BUSINESS_ERRORS as exc:
            raise ToolError(str(exc)) from exc

    def call(kwargs: dict[str, Any]) -> Any:
        decision = {"fault": None, "latency_ms": 0.0}

        def on_decision(fault: str | None, latency_ms: float) -> None:
            decision["fault"] = fault
            decision["latency_ms"] = latency_ms

        try:
            if injector is None:
                result = do(kwargs)
            else:
                try:
                    result = injector.call(
                        service_name,
                        op.name,
                        lambda: do(kwargs),
                        on_decision=on_decision,
                        record_time=_record_time(world, op, kwargs),
                    )
                except FaultTimeout as exc:
                    # The op already ran; the client "timed out". Surface as a tool error so
                    # a retrying agent runs it again (the double-write bug).
                    raise ToolError(f"timeout: {exc}") from exc
                except FaultError as exc:
                    raise ToolError(f"{exc.kind}: {exc}") from exc
        except ToolError as exc:
            _record_trace(recorder, op.name, kwargs, decision, world, ok=False, error=str(exc))
            # A failed call may still have mutated the world (a timeout runs the op, then
            # fails), so mirror state on the error path too — else the snapshot under-reports
            # exactly the write-then-timeout bug worldbench exists to catch.
            _mirror_state(world, state_file)
            raise
        _record_trace(recorder, op.name, kwargs, decision, world, ok=True, result=result)
        print(f"[worldbench] {op.name}({kwargs}) -> {result}", file=sys.stderr)
        _mirror_state(world, state_file)
        return result

    def fn(**kwargs: Any) -> Any:
        return call(kwargs)

    fn.__name__ = op.name
    fn.__signature__ = inspect.Signature(params)
    fn.__annotations__ = {
        p.name: (p.annotation if p.annotation is not _EMPTY else Any) for p in params
    }
    return fn


def _mirror_state(world: World, state_file: str | None) -> None:
    """Mirror the whole world to a JSON file so an out-of-process client can read end state.
    Called after every attempt (success or fault), since a faulted write still mutates."""
    if state_file:
        Path(state_file).write_text(json.dumps(world.snapshot(), indent=2))


def _record_time(world: World, op: OperationSpec, kwargs: dict[str, Any]):
    """The target record's timestamp (first datetime field), for conditional not-found rules.
    Only defined for single-record ops that name an existing record; else None."""
    if op.kind not in ("get", "update", "delete") or "id" not in kwargs:
        return None
    fields = world.table(op.record).record_type.fields
    dt_field = next((n for n, ft in fields.items() if ft.kind == "datetime"), None)
    if dt_field is None:
        return None
    record = world.table(op.record).get(kwargs["id"])
    if record is None or record.get(dt_field) is None:
        return None
    from datetime import datetime  # noqa: PLC0415

    return datetime.fromisoformat(record[dt_field])


def _record_trace(
    recorder: Recorder | None,
    tool: str,
    args: dict[str, Any],
    decision: dict[str, Any],
    world: World,
    *,
    ok: bool,
    result: Any = None,
    error: str | None = None,
) -> None:
    if recorder is None:
        return
    recorder.record(
        tool=tool,
        args=args,
        ok=ok,
        world_rev=world.revision,
        fault=decision["fault"],
        latency_ms=decision["latency_ms"],
        result=result,
        error=error,
    )
