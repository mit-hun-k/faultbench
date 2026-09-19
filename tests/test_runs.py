"""The N-runs / pass-rate / min_pass_rate machinery (milestone 6), tested by running an inner
pytest session with `pytester`. Deterministic and keyless: the inner test passes on even
run indices and fails on odd ones, so a 10-run test is exactly 50% pass rate."""

INNER = """
import pytest

@pytest.mark.runs(10)
{marker}
def test_thing(run_index):
    assert run_index % 2 == 0
"""


def _run(pytester, marker="", *args):
    pytester.makepyfile(INNER.format(marker=marker))
    return pytester.runpytest(*args)


def test_runs_parametrizes_into_n_items(pytester):
    result = _run(pytester)
    # 10 runs: 5 even (pass), 5 odd (fail), and no min_pass_rate so failures are real.
    result.assert_outcomes(passed=5, failed=5)
    result.stdout.fnmatch_lines(["*5/10 passed (50%)*"])


def test_min_pass_rate_met_is_green(pytester):
    result = _run(pytester, "@pytest.mark.min_pass_rate(0.4)")
    # 50% >= 40%: individual failures are absorbed, the suite is green.
    result.assert_outcomes(passed=10)
    assert result.ret == 0
    result.stdout.fnmatch_lines(["*5/10 passed (50%)*PASS*"])


def test_min_pass_rate_missed_fails_ci(pytester):
    result = _run(pytester, "@pytest.mark.min_pass_rate(0.6)")
    # 50% < 60%: items are absorbed to passed, but the session still fails.
    result.assert_outcomes(passed=10)
    assert result.ret != 0
    result.stdout.fnmatch_lines(["*5/10 passed (50%)*FAIL*"])


def test_runs_option_overrides_marker(pytester):
    result = _run(pytester, "", "--runs=4")
    # --runs=4 overrides @runs(10): 4 items (run0..run3), 2 pass / 2 fail.
    result.assert_outcomes(passed=2, failed=2)
    result.stdout.fnmatch_lines(["*2/4 passed (50%)*"])
