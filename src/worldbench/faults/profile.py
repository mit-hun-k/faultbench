"""Fault profile: the parsed `faults:` block. Milestone 4.

A profile maps a key to a rule. The key is either `default` (applies to every operation) or
`service.operation` (applies to one). A rule carries a latency range and a map of error kind
-> probability. `resolve(service, op)` merges the default rule with the specific one.

Conditional errors (e.g. `not_found_if_newer_than: 2h`) and rate limits are parsed and kept
but NOT enforced yet — that is milestone 7. Keeping them here means shop.yaml still loads.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

# Probabilistic error kinds the injector knows how to produce (milestone 4).
KNOWN_ERROR_KINDS = frozenset(
    {"timeout", "http_500", "http_429", "malformed_json", "empty_result", "not_found"}
)
# Keys inside `errors:` that are conditions, not probabilities (enforced in milestone 7).
CONDITIONAL_KEYS = frozenset({"not_found_if_newer_than"})

_DURATION_RE = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*([smhd])\s*$")
_UNIT_SECONDS = {"s": 1, "m": 60, "h": 3600, "d": 86400}


def parse_duration(text: str) -> float:
    """ "2h" -> 7200.0 seconds."""
    m = _DURATION_RE.match(text)
    if not m:
        raise ValueError(f"bad duration {text!r} (expected e.g. '30s', '2h', '1d')")
    return float(m.group(1)) * _UNIT_SECONDS[m.group(2)]


class FaultRule(BaseModel):
    latency_ms: tuple[int, int] | None = None
    errors: dict[str, float] = Field(default_factory=dict)  # kind -> probability
    conditional: dict[str, float] = Field(default_factory=dict)  # cond -> seconds (unenforced)

    @classmethod
    def from_body(cls, body: dict) -> FaultRule:
        latency = body.get("latency_ms")
        if latency is not None:
            latency = tuple(latency)
            if len(latency) != 2 or latency[0] > latency[1]:
                raise ValueError(f"latency_ms must be [lo, hi] with lo <= hi, got {latency}")
        errors: dict[str, float] = {}
        conditional: dict[str, float] = {}
        for kind, value in (body.get("errors") or {}).items():
            if kind in CONDITIONAL_KEYS:
                conditional[kind] = parse_duration(str(value))
            elif kind in KNOWN_ERROR_KINDS:
                errors[kind] = float(value)
            else:
                raise ValueError(
                    f"unknown error kind {kind!r} (known: {sorted(KNOWN_ERROR_KINDS)}, "
                    f"conditional: {sorted(CONDITIONAL_KEYS)})"
                )
        total = sum(errors.values())
        if total > 1.0 + 1e-9:
            raise ValueError(f"error probabilities sum to {total} > 1.0")
        return cls(latency_ms=latency, errors=errors, conditional=conditional)


class FaultProfile(BaseModel):
    rules: dict[str, FaultRule] = Field(default_factory=dict)

    @classmethod
    def from_dict(cls, faults: dict | None) -> FaultProfile:
        rules = {key: FaultRule.from_body(body or {}) for key, body in (faults or {}).items()}
        return cls(rules=rules)

    @classmethod
    def from_world_file(cls, path: str | Path) -> FaultProfile:
        data = yaml.safe_load(Path(path).read_text())
        return cls.from_dict(data.get("faults"))

    def resolve(self, service: str, op: str) -> FaultRule:
        """The effective rule for one operation: default merged with its specific rule."""
        default = self.rules.get("default", FaultRule())
        specific = self.rules.get(f"{service}.{op}")
        if specific is None:
            return default
        return FaultRule(
            latency_ms=specific.latency_ms or default.latency_ms,
            errors={**default.errors, **specific.errors},
            conditional={**default.conditional, **specific.conditional},
        )

    def is_empty(self) -> bool:
        return not self.rules
