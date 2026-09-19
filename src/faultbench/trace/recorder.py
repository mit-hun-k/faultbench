"""JSON Lines recorder: one event per tool call. Milestone 6. See docs/ARCHITECTURE.md §4.

One event per tool call:
    {run, seq, ts, tool, args, fault, latency_ms, ok, result|error, world_rev}
Events are kept in memory (`recorder.events`) and, if a path is given, appended as JSON Lines
so a failing run leaves a readable log on disk.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


class Recorder:
    def __init__(self, run: int = 0, path: str | Path | None = None) -> None:
        self.run = run
        self.events: list[dict] = []
        self._seq = 0
        self._path = Path(path) if path else None
        if self._path:
            self._path.write_text("")  # start each run's file clean

    def record(
        self,
        *,
        tool: str,
        args: dict[str, Any],
        ok: bool,
        world_rev: int,
        fault: str | None = None,
        latency_ms: float = 0.0,
        result: Any = None,
        error: str | None = None,
    ) -> dict:
        event = {
            "run": self.run,
            "seq": self._seq,
            "ts": round(time.time(), 6),
            "tool": tool,
            "args": dict(args),
            "fault": fault,
            "latency_ms": round(float(latency_ms), 3),
            "ok": ok,
            "world_rev": world_rev,
        }
        if ok:
            event["result"] = result
        else:
            event["error"] = error
        self._seq += 1
        self.events.append(event)
        if self._path:
            with self._path.open("a") as fh:
                fh.write(json.dumps(event, default=str) + "\n")
        return event
