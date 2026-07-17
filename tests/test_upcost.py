"""Regression: openga.upcost per-UP variable OPEX (WP4 UPCOST sheet)."""
import pytest

from openga import upcost, finance
from openga.config import DEFAULT


def test_variable_total(baseline):
    """Per-UP variable total (AUD/kg) == finance variable subtotal / Q."""
    u = upcost.run(DEFAULT)
    fin_var_per_kg = baseline["finance"]["opex_variable"] / DEFAULT.meb.cap_prod
    assert u.variable_total_per_kg == pytest.approx(fin_var_per_kg, rel=1e-9)


def test_up1_electricity_only():
    """UP1 has only an electricity cost line (WP4 UPCOST!M5 = 6.0405 AUD/kg)."""
    u = upcost.run(DEFAULT)
    up1 = next(x for x in u.per_up if x.name.startswith("UP1"))
    assert set(up1.lines) == {"electricity"}
    assert up1.total == pytest.approx(6.04053689320388, rel=1e-9)


def test_reconciliation_zero():
    assert upcost.reconcile(DEFAULT) == pytest.approx(0.0, abs=1e-6)


def test_fixed_not_allocated():
    """Fixed OPEX is plant-level only; no UP carries labour/maintenance/insurance."""
    u = upcost.run(DEFAULT)
    for uc in u.per_up:
        assert "labour" not in uc.lines
        assert "maintenance" not in uc.lines
