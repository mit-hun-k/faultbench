"""Query a recorded trace. Milestone 6. See docs/ARCHITECTURE.md §4.

A `Trace` is a thin read-only view over a list of events. When constructed from a live
Recorder's `events` list it reflects calls as they happen, so a test can assert on it after
running the agent.
"""

from __future__ import annotations

import json
from pathlib import Path


class Trace:
    def __init__(self, events: list[dict]) -> None:
        self._events = events

    @classmethod
    def from_file(cls, path: str | Path) -> Trace:
        lines = Path(path).read_text().splitlines()
        return cls([json.loads(line) for line in lines if line.strip()])

    @property
    def events(self) -> list[dict]:
        return list(self._events)

    def count(self, tool: str) -> int:
        return sum(1 for e in self._events if e["tool"] == tool)

    def calls_to(self, tool: str) -> list[dict]:
        return [e for e in self._events if e["tool"] == tool]

    def faults(self) -> list[dict]:
        return [e for e in self._events if e.get("fault")]

    def failures(self) -> list[dict]:
        return [e for e in self._events if not e["ok"]]

    def summary(self) -> str:
        """A one-line trace summary for failure reports."""
        parts = []
        for e in self._events:
            label = e["tool"]
            if e.get("fault"):
                label += f"!{e['fault']}"
            elif not e["ok"]:
                label += "!error"
            parts.append(label)
        return " → ".join(parts) if parts else "(no calls)"

    def __len__(self) -> int:
        return len(self._events)

    def __iter__(self):
        return iter(list(self._events))
