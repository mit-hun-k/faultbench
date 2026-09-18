"""pytest plugin: world/faults/clock/mcp_server fixtures and markers. Milestone 5.

Registered via the `pytest11` entry point in pyproject.toml, so it loads automatically once
worldbench is installed. A test declares what it needs with markers and receives ready-built
objects as fixtures:

    @pytest.mark.world("worlds/shop.yaml")
    @pytest.mark.faults({"payments.issue_refund": {"errors": {"timeout": 1.0}}})
    def test_x(world, mcp_server, clock):
        ...

`--runs=N` pass-rate reporting and the trace fixture are milestone 6; this milestone is
fixtures + markers + a first green test. There is no `mcp_url` (HTTP) yet — `mcp_server` is
an in-process MCP server sharing the `world` object, so a test can assert on world state
directly. HTTP is milestone 8.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from .faults import FakeClock, FaultProfile
from .server import build_server
from .world import World


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "world(path): load a world.yaml for this test")
    config.addinivalue_line("markers", "faults(spec): fault profile path or dict for this test")
    config.addinivalue_line("markers", "runs(n): repeat this test n times with different seeds")
    config.addinivalue_line("markers", "min_pass_rate(r): fail if pass rate over runs is below r")


def _marker(request: pytest.FixtureRequest, name: str):
    marker = request.node.get_closest_marker(name)
    if marker is None:
        return None
    if not marker.args:
        raise pytest.UsageError(f"@pytest.mark.{name} needs an argument")
    return marker.args[0]


def _resolve(request: pytest.FixtureRequest, path: str) -> Path:
    """Resolve a marker path relative to the test file's directory."""
    p = Path(path)
    return p if p.is_absolute() else (Path(request.path).parent / p).resolve()


@pytest.fixture
def world(request: pytest.FixtureRequest) -> World:
    """The stateful world for this test, from `@pytest.mark.world("path.yaml")`."""
    path = _marker(request, "world")
    if path is None:
        raise pytest.UsageError("the `world` fixture needs @pytest.mark.world('path.yaml')")
    return World.load(_resolve(request, path))


@pytest.fixture
def faults(request: pytest.FixtureRequest) -> FaultProfile:
    """The fault profile for this test, from `@pytest.mark.faults(path | dict)`. Empty if the
    marker is absent (a fault-free test does not inherit the world file's faults)."""
    spec = _marker(request, "faults")
    if spec is None:
        return FaultProfile.from_dict({})
    if isinstance(spec, dict):
        return FaultProfile.from_dict(spec)
    return FaultProfile.from_world_file(_resolve(request, spec))


@pytest.fixture
def clock() -> FakeClock:
    """A FakeClock at its default 'now'; a test can advance() or set() it."""
    return FakeClock()


@pytest.fixture
def mcp_server(world: World, faults: FaultProfile):
    """An in-process MCP server built from `world` (+ `faults`). It shares the `world` object,
    so a test can drive the tools and then assert on `world` directly.

    The `clock` is intentionally NOT threaded in yet: doing so activates time-dependent rules
    (e.g. the shop's 30-day return window) while the seed dates and the clock's 'now' are not
    aligned. That alignment and clock-driven faults land in milestone 7; until then the server
    runs clock-free (no window enforcement), matching milestones 3–4."""
    return build_server(world, clock=None, faults=faults)
