"""Regression: openga.validation Wesselkaemper engine vs published targets."""
import pytest

from openga import validation, sensitivity
from openga.config import DEFAULT

REL = 1e-9


@pytest.fixture(scope="module")
def w():
    return validation.wesselkaemper(DEFAULT)


def test_engine_values(w, baseline):
    b = baseline["wesselkaemper"]
    assert w.lcop_base == pytest.approx(b["lcop_base"], rel=REL)
    assert w.capital_component == pytest.approx(b["capital_component"], rel=REL)
    assert w.lcop_s1 == pytest.approx(b["lcop_s1"], rel=REL)
    assert w.lcop_s2 == pytest.approx(b["lcop_s2"], rel=REL)
    assert w.lcop_grant == pytest.approx(b["lcop_grant"], rel=REL)


def test_all_tests_pass(w):
    assert w.all_pass()
    validation.assert_wesselkaemper(DEFAULT)


def test_published_targets_within_tolerance(w, baseline):
    t = baseline["wesselkaemper"]["targets"]
    tol = {"A. Base-case LCOP": ("base", 0.05),
           "A. Capital component": ("capital", 0.10),
           "B. Out-of-sample S1 (6.5% CAGR cap)": ("s1", 0.10),
           "B. Out-of-sample S2 (9.5% CAGR cap)": ("s2", 0.10),
           "C. US$120M grant scenario": ("grant", 0.10)}
    for test in w.tests:
        key, tolerance = tol[test.name]
        assert test.target == pytest.approx(t[key])
        assert abs(test.deviation) <= tolerance


def test_breakeven_curve(baseline):
    pts = {p.feed_mg_l: p.mvp for p in sensitivity.breakeven_feed(DEFAULT)}
    assert pts[50] == pytest.approx(baseline["breakeven"]["50"], rel=REL)
    assert pts[100] == pytest.approx(baseline["breakeven"]["100"], rel=REL)


def test_breakeven_monotonic_decreasing():
    """MVP falls as feed concentration rises (electricity intensity drops)."""
    pts = sensitivity.breakeven_feed(DEFAULT)
    mvps = [p.mvp for p in pts]
    assert all(a >= b for a, b in zip(mvps, mvps[1:]))
