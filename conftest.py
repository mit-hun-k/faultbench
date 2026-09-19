"""Repo-root conftest: enable pytest's `pytester` fixture so tests/test_runs.py can run the
runs/pass-rate machinery in an inner pytest session."""

pytest_plugins = ["pytester"]
