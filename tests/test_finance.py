"""Regression: openga.finance vs WP4 CAPEX/OPEX/DEPREC/LCOP cached values."""
import pytest

from openga import finance, upcost
from openga.config import DEFAULT

REL = 1e-9


@pytest.fixture(scope="module")
def fr():
    return finance.run(DEFAULT)


def test_capex(fr, baseline):
    b = baseline["finance"]
    assert fr.fci == pytest.approx(b["fci"], rel=REL)
    assert fr.working_capital == pytest.approx(b["working_capital"], rel=REL)


def test_opex(fr, baseline):
    b = baseline["finance"]
    assert fr.opex_variable == pytest.approx(b["opex_variable"], rel=REL)
    assert fr.opex_fixed == pytest.approx(b["opex_fixed"], rel=REL)
    assert fr.opex_total == pytest.approx(b["opex_total"], rel=REL)


def test_depreciation_pv(fr, baseline):
    assert fr.pv_depreciation == pytest.approx(baseline["finance"]["pv_depreciation"], rel=REL)


def test_deprec_totals_equal_fci():
    """DEPREC totals = FCI under both methods (WP4 verification #2)."""
    sched = finance.depreciation_schedule(DEFAULT, 1.0)
    assert sum(sched["SL"]) == pytest.approx(1.0, rel=1e-12)
    assert sum(sched["DV"]) == pytest.approx(1.0, rel=1e-12)


def test_lcop_and_mvp(fr, baseline):
    b = baseline["finance"]
    assert fr.lcop_pretax == pytest.approx(b["lcop_pretax"], rel=REL)
    assert fr.mvp == pytest.approx(b["mvp"], rel=REL)


def test_mvp_makes_npv_zero(fr):
    """CASHFLOW verification: NPV(p*) ~ 0 (validates the closed-form identity)."""
    assert finance.npv_at_price(fr.mvp) == pytest.approx(0.0, abs=1e-3)


def test_cost_stack_sums_to_lcop(fr):
    """LCOP cost-stack total = pre-tax LCOP (WP4 verification #3)."""
    assert sum(fr.cost_stack.values()) == pytest.approx(fr.lcop_pretax, rel=1e-9)


def test_upcost_reconciliation():
    """sum(per-UP variable OPEX) == finance variable subtotal (UPCOST invariant)."""
    assert upcost.reconcile(DEFAULT) == pytest.approx(0.0, abs=1e-6)


def test_bottom_up_capex_toggle():
    cfg = DEFAULT.with_(capex=DEFAULT.capex.__class__(method=2))
    assert finance.fci(cfg, equipment=[1_000_000, 2_000_000]) == pytest.approx(3_000_000 * 4.74)
