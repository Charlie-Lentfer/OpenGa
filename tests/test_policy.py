"""Regression: openga.policy scenarios, CMPTI boundary, baseline neutrality."""
import pytest

from openga import policy, finance
from openga.config import DEFAULT

REL = 1e-9


def test_baseline_neutrality():
    """Baseline policy = zero deviation from unmodified finance output."""
    assert policy.assert_baseline_neutral(DEFAULT) == pytest.approx(0.0, abs=1e-9)
    assert policy.run(1).mvp == pytest.approx(finance.run(DEFAULT).mvp, rel=1e-12)


def test_cmpti_eligible_base(baseline):
    """OPEX!F24 eligible base (electricity..labour eligible; %FCI & feedstock not)."""
    assert policy.cmpti_eligible_base(DEFAULT) == pytest.approx(
        baseline["finance"]["cmpti_eligible_base"], rel=REL)


def test_cmpti_efa_lowers_mvp():
    """Scenario 2 (10% offset + low WACC) reduces p* below baseline."""
    assert policy.run(2).mvp < policy.run(1).mvp


def test_price_floor_not_wired():
    """CMSR floor is carried as an OPEN TODO and must NOT change p*."""
    baseline_mvp = policy.run(1).mvp
    scen3 = policy.run(3)
    # scenario 3 has offset 0 and WACC base -> identical p* to baseline
    assert scen3.mvp == pytest.approx(baseline_mvp, rel=1e-12)
    assert "deferred" in scen3.price_floor_status.lower()


def test_eligibility_flags():
    e = policy.CMPTI_ELIGIBILITY
    assert e["feedstock"] == 0 and e["maintenance"] == 0 and e["insurance"] == 0
    assert e["electricity"] == 1 and e["labour"] == 1
