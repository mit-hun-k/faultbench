"""pytest plugin: world/faults/clock/mcp_url/trace fixtures, markers, --runs. Milestone 5-6.

Registered via the `pytest11` entry point in pyproject.toml, so it loads automatically
once worldbench is installed.
"""

import pytest


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "world(path): load a world.yaml for this test")
    config.addinivalue_line("markers", "faults(spec): fault profile path or dict for this test")
    config.addinivalue_line("markers", "runs(n): repeat this test n times with different seeds")
    config.addinivalue_line("markers", "min_pass_rate(r): fail if pass rate over runs is below r")
