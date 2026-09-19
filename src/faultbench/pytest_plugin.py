"""pytest plugin: world/faults/clock/mcp_server/mcp_url/trace fixtures, markers, and N-run
pass rate. Milestones 5–8.

Registered via the `pytest11` entry point in pyproject.toml, so it loads automatically once
faultbench is installed. A test declares what it needs with markers and receives ready-built
objects as fixtures:

    @pytest.mark.world("worlds/shop.yaml")
    @pytest.mark.faults({"payments.issue_refund": {"errors": {"timeout": 0.1}}})
    @pytest.mark.runs(20)
    @pytest.mark.min_pass_rate(0.9)
    def test_refund(world, mcp_server, trace):
        ...

Runs: `@pytest.mark.runs(N)` (or `--runs=N`, which overrides it) executes the test N times,
each with a distinct deterministic fault sequence (`run_index` 0..N-1). The plugin reports
`passed/total (rate)` per test with a short trace for each failing run. `min_pass_rate(r)`
makes the aggregate the CI verdict: individual run failures don't fail the build, only a rate
below `r` does. Without `min_pass_rate`, every run must pass.

Transports: `mcp_server` is an in-process MCP server sharing the `world` object, so a test
can assert on world state directly. `mcp_url` serves the world over HTTP in a subprocess (any
MCP client can connect); assert on end state via `mcp_url.snapshot()`.
"""

from __future__ import annotations

import json
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

from .faults import FakeClock, FaultProfile
from .server import build_server
from .trace import Recorder, Trace
from .world import World


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "world(path): load a world.yaml for this test")
    config.addinivalue_line("markers", "faults(spec): fault profile path or dict for this test")
    config.addinivalue_line("markers", "runs(n): repeat this test n times with different seeds")
    config.addinivalue_line("markers", "min_pass_rate(r): fail if pass rate over runs is below r")
    config._wb_runs = {}  # base nodeid -> aggregate {n, min, passed, failed, failures}


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--runs", type=int, default=None, help="override @pytest.mark.runs(N) for all tests"
    )


# --- markers / helpers ----------------------------------------------------------


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


def _runs_count(config: pytest.Config, definition) -> int:
    option = config.getoption("runs")
    if option:
        return option
    marker = definition.get_closest_marker("runs")
    return int(marker.args[0]) if marker and marker.args else 1


def _min_pass_rate(marker) -> float | None:
    return float(marker.args[0]) if marker and marker.args else None


# --- fixtures -------------------------------------------------------------------


@pytest.fixture
def run_index(request: pytest.FixtureRequest) -> int:
    """The current run's index (0-based). Parametrised when a test uses @runs(N)/--runs."""
    return getattr(request, "param", 0)


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
def _recorder(run_index: int) -> Recorder:
    return Recorder(run=run_index)


@pytest.fixture
def trace(_recorder: Recorder) -> Trace:
    """A live view of the tool calls recorded this run."""
    return Trace(_recorder.events)


@pytest.fixture
def mcp_server(
    world: World, faults: FaultProfile, clock: FakeClock, run_index: int, _recorder: Recorder
):
    """An in-process MCP server built from `world` (+ `faults`, `clock`, this run's
    `run_index`, and a recorder feeding the `trace` fixture). It shares the `world` object and
    the `clock`, so a test can drive the tools, move the clock, and then assert on `world`
    directly. Seed dates are aligned with the clock's default 'now' (milestone 7), so
    delivered orders are eligible for return unless the test moves the clock forward."""
    return build_server(world, clock=clock, faults=faults, run_index=run_index, recorder=_recorder)


class _ServerURL(str):
    """The MCP endpoint URL, with `.snapshot()` reading the out-of-process server's world
    state (mirrored to a file, since an HTTP server can't share the `world` object)."""

    state_file: Path

    def snapshot(self) -> dict:
        try:
            return json.loads(self.state_file.read_text())
        except (FileNotFoundError, ValueError):
            return {}


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_for_port(host: str, port: int, proc: subprocess.Popen, timeout: float = 15.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"faultbench server exited early (code {proc.returncode})")
        with socket.socket() as s:
            s.settimeout(0.5)
            try:
                s.connect((host, port))
                return
            except OSError:
                time.sleep(0.1)
    raise TimeoutError(f"faultbench server did not come up on {host}:{port} in {timeout}s")


@pytest.fixture
def mcp_url(request: pytest.FixtureRequest, tmp_path: Path):
    """A running MCP server over HTTP: spawns `faultbench serve --http` as a subprocess and
    yields its URL. Use `mcp_url.snapshot()` to read the world's end state. `@pytest.mark.faults`
    (if present) applies the world file's own faults: block (inline dict faults aren't
    supported over HTTP)."""
    world_path = _marker(request, "world")
    if world_path is None:
        raise pytest.UsageError("the `mcp_url` fixture needs @pytest.mark.world('path.yaml')")
    host, port = "127.0.0.1", _free_port()
    state_file = tmp_path / "state.json"
    cmd = [
        sys.executable,
        "-m",
        "faultbench.cli",
        "serve",
        str(_resolve(request, world_path)),
        "--http",
        "--host",
        host,
        "--port",
        str(port),
        "--state-file",
        str(state_file),
    ]
    if request.node.get_closest_marker("faults") is not None:
        cmd.append("--faults")
    proc = subprocess.Popen(cmd)
    try:
        _wait_for_port(host, port, proc)
        url = _ServerURL(f"http://{host}:{port}/mcp")
        url.state_file = state_file
        yield url
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


# --- N runs + pass rate ---------------------------------------------------------


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    if "run_index" not in metafunc.fixturenames:
        return
    n = _runs_count(metafunc.config, metafunc.definition)
    if n <= 1:
        return
    base = metafunc.definition.nodeid
    metafunc.config._wb_runs[base] = {
        "n": n,
        "min": _min_pass_rate(metafunc.definition.get_closest_marker("min_pass_rate")),
        "passed": 0,
        "failed": 0,
        "failures": [],
    }
    metafunc.parametrize("run_index", range(n), indirect=True, ids=[f"run{i}" for i in range(n)])


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo):
    outcome = yield
    report = outcome.get_result()
    if report.when != "call":
        return
    groups = getattr(item.config, "_wb_runs", {})
    base = item.nodeid.split("[")[0]
    group = groups.get(base)
    if group is None:
        return
    if report.passed:
        group["passed"] += 1
    elif report.failed:
        group["failed"] += 1
        summary = ""
        rec = item.funcargs.get("_recorder")
        if rec is not None:
            summary = Trace(rec.events).summary()
        run_idx = item.callspec.params.get("run_index") if hasattr(item, "callspec") else "?"
        group["failures"].append((run_idx, summary))
        # With min_pass_rate, a single failing run must not fail CI — the aggregate decides.
        if group["min"] is not None:
            report.outcome = "passed"
            report.longrepr = None


def _done(group: dict) -> int:
    return group["passed"] + group["failed"]


def _rate(group: dict) -> float:
    done = _done(group)
    return group["passed"] / done if done else 0.0


def pytest_terminal_summary(terminalreporter, exitstatus, config: pytest.Config) -> None:
    groups = {b: g for b, g in getattr(config, "_wb_runs", {}).items() if _done(g)}
    if not groups:
        return
    tr = terminalreporter
    tr.write_sep("=", "faultbench: pass rate over runs")
    for base, group in groups.items():
        # A run group can be trimmed by -k/-x; report over what actually ran.
        rate = _rate(group)
        line = f"{base}: {group['passed']}/{_done(group)} passed ({rate:.0%})"
        if group["min"] is not None:
            ok = rate >= group["min"]
            line += f"  min_pass_rate={group['min']:.0%} -> {'PASS' if ok else 'FAIL'}"
        tr.write_line(line)
        for run_idx, summary in group["failures"][:5]:
            tr.write_line(f"    run{run_idx}: {summary}")


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    groups = getattr(session.config, "_wb_runs", {})
    for group in groups.values():
        if group["min"] is not None and _done(group) and _rate(group) < group["min"]:
            session.exitstatus = pytest.ExitCode.TESTS_FAILED
            return
