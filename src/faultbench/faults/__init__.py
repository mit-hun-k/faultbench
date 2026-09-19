"""faultbench.faults — see docs/ARCHITECTURE.md."""

from .clock import DEFAULT_NOW, FakeClock
from .injector import FaultError, FaultTimeout, Injector
from .profile import FaultProfile, FaultRule, parse_duration

__all__ = [
    "FakeClock",
    "DEFAULT_NOW",
    "FaultProfile",
    "FaultRule",
    "parse_duration",
    "Injector",
    "FaultTimeout",
    "FaultError",
]
