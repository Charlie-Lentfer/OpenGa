"""
openga.policy
=============
Policy scenario layer (WP4 POLICY sheet).

Three placeholder scenarios, mechanics wired:
    1  Baseline (no policy support)          offset 0,   WACC base, floor 0
    2  CMPTI + EFA facility financing        offset 10%, WACC low,  floor 0
    3  CMSR offtake guarantee                offset 0,   WACC base, floor 600

Each scenario is expressed as an OPEX offset (feeds the p* algebra), a WACC
case (selects FIN low/base/high) and a price floor.

*** OPEN TODO (revenue-side mechanism) ***
The price floor is INTENTIONALLY NOT WIRED into the minimum-viable-price
calculation.  The CMSR contract mechanics (contract-for-difference vs floor
purchase) are not yet specified; wiring a floor into p* now would silently
bake in an unvalidated revenue assumption.  It is carried here as metadata and
surfaced by `price_floor_status()` only.  Do NOT implement it in finance.mvp
until the mechanism is designed.

CMPTI eligibility boundary mirrors OPEX!H (per-line eligible/ineligible flags).
The offset currently applies to total OPEX (documented simplification); the
eligible base is computed for when the design is finalised.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

from .config import Config, PolicyScenario, POLICY_SCENARIOS, DEFAULT
from . import finance as _fin
from . import meb as _meb

# CMPTI eligibility flags (OPEX!H column).  1 = eligible, 0 = ineligible.
CMPTI_ELIGIBILITY: Dict[str, int] = {
    "electricity": 1, "steam": 1, "h2so4": 1, "naoh": 1, "cao": 1, "hcl": 1,
    "resin": 1, "water": 1, "salty_disposal": 1, "residue_disposal": 1,
    "feedstock": 0,          # Div 419 excludes feedstock costs
    "labour": 1,
    "maintenance": 0,        # %FCI-derived: capital-linked, ineligible
    "insurance": 0,          # %FCI-derived: capital-linked, ineligible
}

PRICE_FLOOR_TODO = (
    "Revenue-side price floor is deferred (OPEN TODO): CMSR contract mechanics "
    "undecided; not wired into p*. See policy module docstring.")


def scenario(sel: int) -> PolicyScenario:
    return POLICY_SCENARIOS[sel]


def cmpti_eligible_base(cfg: Config = DEFAULT,
                        meb_result: Optional[_meb.MebResult] = None) -> float:
    """
    Annual CMPTI-eligible OPEX base (AUD/yr) -- OPEX!F24.
    Provided for future re-pointing of the offset; currently the offset applies
    to total OPEX (documented simplification).
    """
    res = meb_result or _meb.run(cfg)
    var = _fin.annual_variable_opex(cfg, res)
    fixed = _fin.annual_fixed_opex(cfg)
    base = 0.0
    for k, v in var.items():
        base += CMPTI_ELIGIBILITY.get(k, 0) * v
    for k, v in fixed.items():
        base += CMPTI_ELIGIBILITY.get(k, 0) * v
    return base


@dataclass
class PolicyResult:
    selection: int
    scenario: PolicyScenario
    finance: _fin.FinanceResult
    cmpti_eligible_base: float
    price_floor_status: str

    @property
    def mvp(self) -> float:
        return self.finance.mvp


def run(sel: int = 1, cfg: Config = DEFAULT,
        meb_result: Optional[_meb.MebResult] = None) -> PolicyResult:
    """Run the financial model under policy scenario `sel` (1-3)."""
    sc = scenario(sel)
    res = meb_result or _meb.run(cfg)
    fr = _fin.run(cfg, policy=sc, meb_result=res)
    floor_status = (PRICE_FLOOR_TODO if sc.price_floor > 0
                    else "no floor (baseline)")
    return PolicyResult(sel, sc, fr, cmpti_eligible_base(cfg, res), floor_status)


def assert_baseline_neutral(cfg: Config = DEFAULT, tol: float = 1e-9) -> float:
    """
    Baseline-neutrality invariant: selecting the baseline policy must produce
    ZERO deviation from the unmodified finance.run() output.  Returns the p*
    deviation (should be 0).  Also checks the scenario-1 parameter row.
    """
    sc = scenario(1)
    assert sc.opex_offset == 0.0, "baseline OPEX offset must be 0"
    assert sc.wacc_case == 2, "baseline WACC case must be 2 (merchant base)"
    assert sc.price_floor == 0.0, "baseline price floor must be 0"
    unmodified = _fin.run(cfg)                 # finance default = baseline
    via_policy = run(1, cfg).finance
    dev = via_policy.mvp - unmodified.mvp
    assert abs(dev) <= tol, f"baseline not neutral: p* deviation {dev:.3e}"
    return dev


def price_floor_status() -> str:
    return PRICE_FLOOR_TODO


__all__ = ["CMPTI_ELIGIBILITY", "PRICE_FLOOR_TODO", "scenario",
           "cmpti_eligible_base", "PolicyResult", "run",
           "assert_baseline_neutral", "price_floor_status"]
