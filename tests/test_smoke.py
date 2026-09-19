"""Scaffold smoke tests. Replace with real tests as milestones land."""

import tomllib
from pathlib import Path

import worldbench
from worldbench.cli import main


def test_version_is_set():
    assert worldbench.__version__


def test_version_matches_pyproject():
    pyproject = tomllib.loads((Path(__file__).resolve().parents[1] / "pyproject.toml").read_text())
    assert worldbench.__version__ == pyproject["project"]["version"]


def test_cli_help_runs():
    assert main([]) == 0


def test_pytest_markers_registered(pytestconfig):
    markers = pytestconfig.getini("markers")
    joined = "\n".join(markers)
    for name in ("world(", "faults(", "runs(", "min_pass_rate("):
        assert name in joined
