"""Regression: openga.meb vs WP3 cached values + elemental closure."""
import math

import pytest

from openga import meb
from openga.config import DEFAULT, MebInputs

REL = 1e-9


@pytest.fixture(scope="module")
def res():
    return meb.run(DEFAULT)


def test_headline_targets(res, baseline):
    b = baseline["meb"]
    assert res.throughput_t == pytest.approx(b["throughput_t"], rel=REL)
    assert res.electricity_kwh == pytest.approx(b["electricity_kwh"], rel=REL)
    assert res.thermal_kwh == pytest.approx(b["thermal_kwh"], rel=REL)
    assert res.overall_recovery == pytest.approx(b["overall_recovery"], rel=REL)


def test_export_vector(res, baseline):
    b = baseline["meb"]
    e = res.export
    assert e["steam_kg"] == pytest.approx(b["steam_kg"], rel=REL)
    assert e["h2so4_kg"] == pytest.approx(b["h2so4_kg"], rel=REL)
    assert e["naoh_kg"] == pytest.approx(b["naoh_kg"], rel=REL)
    assert e["cao_kg"] == pytest.approx(b["cao_kg"], rel=REL)
    assert e["hcl_kg"] == pytest.approx(b["hcl_kg"], rel=REL)
    assert e["resin_kg"] == pytest.approx(b["resin_kg"], rel=REL)
    assert e["fresh_water_kg"] == pytest.approx(b["fresh_water_kg"], rel=REL)
    assert e["salty_reject_kg"] == pytest.approx(b["salty_reject_kg"], rel=REL)
    assert e["solid_residue_kg"] == pytest.approx(b["solid_residue_kg"], rel=REL)


def test_all_checks_zero(res):
    assert res.master_check <= meb.CLOSE_TOL
    meb.assert_closed(res)


def test_elemental_closures(res):
    c = res.closure
    assert abs(c.sulfur) < 1e-9
    assert abs(c.sodium) < 1e-9
    assert abs(c.chlorine) < 1e-12


def test_per_up_total_matches_export(res):
    for k in meb.QTY_KEYS:
        s = sum(row.get(k, 0.0) for row in res.per_up)
        assert s == pytest.approx(res.export[k], rel=1e-12, abs=1e-12)


def test_baseline_throughput_ratio(res):
    """Baseline (Luo-conc) throughput 21.877 t/kg and RatioT 2.233 (INPUTS D07/D08)."""
    assert res.derived.thru_kg_b == pytest.approx(21876.9930203718, rel=1e-9)
    assert res.derived.ratio_t == pytest.approx(2.23300970873786, rel=1e-9)


def test_scenario1_switches_feed():
    """Scenario 1 resolves feed Ga to the Luo column (230 mg/L, hardness 150)."""
    cfg = DEFAULT.with_(meb=MebInputs(scenario=1))
    a = cfg.meb.active()
    assert a.ga_feed == 230.0
    assert a.hard_site == 150.0
