"""
openga.validation
=================
External-model validation engines.

1. Luo carbon/physics validation  -> delegates to openga.carbon.validate_luo
   (recompute GWP with the China grid EF + Luo inventory; requires scenario 1
   + resin preset 4 for a true replication).

2. Wesselkaemper et al. 2025 year-indexed replication engine (WP4 WESS_REP).
   SI-parameterised, zero fitted values.  Capital schedule 15/70/15 over years
   0-2, production years 3-32, decommissioning tail at year 33, demand-anchor
   toggle.  One engine, four tests (A base + capital component, B out-of-sample
   S1/S2, C grant).  All figures in 2024 USD, independent of the AUD model.

   Engine results vs published targets (tolerances as designed):
       A base LCOP        434.18  vs 421.98  (+/-5%)   PASS
       A capital comp.    252.91  vs 240.71  (+/-10%)  PASS
       B S1 (6.5% cap)    685.04  vs 663.97  (+/-10%)  PASS
       B S2 (9.5% cap)    585.67  vs 568.11  (+/-10%)  PASS
       C grant scenario   299.02  vs 291.60  (+/-10%)  PASS

RETIRED CIRCULAR CHECKS (documented history only -- do NOT reinstate as live
tests):  the earlier VALIDATION sheet solved the discount rate back from an
implied flat-annuity factor (r ~ 7.33%) and derived the plant CAPEX
(US$221.55M) from the published grant arithmetic.  Both were partially
circular (the base-case PASS was true by construction until the SI's stated
capital cost / rate / lifetime were entered).  They are superseded by this
year-indexed engine, which uses SI inputs directly and is retained only as an
audit trail.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .config import Config, WessParams, DEFAULT
from . import carbon as _carbon


# ---------------------------------------------------------------------------
# 1. Luo carbon validation (thin wrapper)
# ---------------------------------------------------------------------------
def validate_luo(cfg: Config = DEFAULT, published_gwp: Optional[float] = None,
                 tolerance: float = 0.10):
    return _carbon.validate_luo(cfg, published_gwp, tolerance)


# ---------------------------------------------------------------------------
# 2. Wesselkaemper year-indexed engine
# ---------------------------------------------------------------------------
@dataclass
class WessYear:
    t: int
    df: float
    capital: float
    capital_grant: float
    fixed_opex: float
    nameplate_prod: float
    demand_s1: float
    demand_s2: float
    sold_s1: float
    sold_s2: float
    decom: float


def _build_years(p: WessParams) -> List[WessYear]:
    years: List[WessYear] = []
    capex = p.capex_usd_m * 1_000_000
    prod_end = p.prod_start_year + p.productive_years - 1     # inclusive (=32)
    anchor = 0 if p.demand_anchor == 1 else p.prod_start_year
    for t in range(0, p.decom_year + 1):                     # 0..33
        df = (1 + p.discount_rate) ** -t
        share = {0: p.cap_share_y0, 1: p.cap_share_y1, 2: p.cap_share_y2}.get(t, 0.0)
        capital = capex * share
        grant = capital * (1 - p.grant_usd_m / p.capex_usd_m)   # pro-rata grant
        in_prod = p.prod_start_year <= t <= prod_end
        fixed = p.fixed_opex_per_kg_nameplate * p.nameplate_kg if in_prod else 0.0
        nameplate = p.nameplate_kg if in_prod else 0.0
        d1 = p.us_demand_2023_kg * (1 + p.cagr_s1) ** (t - anchor) if in_prod else 0.0
        d2 = p.us_demand_2023_kg * (1 + p.cagr_s2) ** (t - anchor) if in_prod else 0.0
        decom = p.decom_pct * capex if t == p.decom_year else 0.0
        years.append(WessYear(t, df, capital, grant, fixed, nameplate,
                              d1, d2, min(nameplate, d1), min(nameplate, d2), decom))
    return years


def _sp(years: List[WessYear], attr: str) -> float:
    return sum(y.df * getattr(y, attr) for y in years)


@dataclass
class WessTest:
    name: str
    engine: float
    target: float
    tolerance: float

    @property
    def deviation(self) -> float:
        return self.engine / self.target - 1

    @property
    def status(self) -> str:
        return "PASS" if abs(self.deviation) <= self.tolerance else "REVIEW"


@dataclass
class WessResult:
    lcop_base: float
    capital_component: float
    lcop_s1: float
    lcop_s2: float
    lcop_grant: float
    pv_production_base: float
    tests: List[WessTest] = field(default_factory=list)

    def all_pass(self) -> bool:
        return all(t.status == "PASS" for t in self.tests)

    def summary(self) -> Dict[str, float]:
        return {
            "lcop_base": self.lcop_base,
            "capital_component": self.capital_component,
            "lcop_s1": self.lcop_s1,
            "lcop_s2": self.lcop_s2,
            "lcop_grant": self.lcop_grant,
        }


def wesselkaemper(cfg: Config = DEFAULT) -> WessResult:
    """Run the SI-parameterised year-indexed replication engine."""
    p = cfg.wess
    years = _build_years(p)

    pv_prod_base = _sp(years, "nameplate_prod")
    pv_prod_s1 = _sp(years, "sold_s1")
    pv_prod_s2 = _sp(years, "sold_s2")
    pv_cap = _sp(years, "capital")
    pv_grant = _sp(years, "capital_grant")
    pv_fixed = _sp(years, "fixed_opex")
    pv_decom = _sp(years, "decom")
    v = p.var_opex_per_kg

    pv_cost_base = pv_cap + pv_fixed + v * pv_prod_base + pv_decom
    pv_cost_s1 = pv_cap + pv_fixed + v * pv_prod_s1 + pv_decom
    pv_cost_s2 = pv_cap + pv_fixed + v * pv_prod_s2 + pv_decom
    pv_cost_grant = pv_grant + pv_fixed + v * pv_prod_base + pv_decom

    lcop_base = pv_cost_base / pv_prod_base
    lcop_s1 = pv_cost_s1 / pv_prod_s1
    lcop_s2 = pv_cost_s2 / pv_prod_s2
    lcop_grant = pv_cost_grant / pv_prod_base
    cap_comp = (pv_cap + pv_decom) / pv_prod_base

    tests = [
        WessTest("A. Base-case LCOP", lcop_base, p.target_base, 0.05),
        WessTest("A. Capital component", cap_comp, p.target_capital, 0.10),
        WessTest("B. Out-of-sample S1 (6.5% CAGR cap)", lcop_s1, p.target_s1, 0.10),
        WessTest("B. Out-of-sample S2 (9.5% CAGR cap)", lcop_s2, p.target_s2, 0.10),
        WessTest("C. US$120M grant scenario", lcop_grant, p.target_grant, 0.10),
    ]
    return WessResult(lcop_base, cap_comp, lcop_s1, lcop_s2, lcop_grant,
                      pv_prod_base, tests)


def assert_wesselkaemper(cfg: Config = DEFAULT) -> WessResult:
    res = wesselkaemper(cfg)
    failing = [t.name for t in res.tests if t.status != "PASS"]
    assert not failing, f"Wesselkaemper replication failed: {failing}"
    return res


__all__ = ["validate_luo", "WessYear", "WessTest", "WessResult",
           "wesselkaemper", "assert_wesselkaemper"]
