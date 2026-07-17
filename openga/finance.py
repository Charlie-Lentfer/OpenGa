"""
openga.finance
==============
Techno-economic financial model (WP4: CAPEX / FIN / OPEX / DEPREC / LCOP).

Headline output: MINIMUM VIABLE PRICE p* (AUD/kg 4N Ga, post-tax NPV = 0),
plus the pre-tax LCOP and the cost stack.

Conventions (WP4 README): real, constant-price cash flows discounted at a real
WACC; all CAPEX in Year 0; 30-year steady state; tax = T x EBIT with immediate
group loss offset; SENS/MC use the SL closed form.

Closed-form identities (LCOP sheet):
    LCOP = [FCI + WC(1-v^n) - S v^n + (1-c) X A] / (Q A)
    p*   = [FCI + WC(1-v^n) - S v^n - T*PVdep + (1-T-c) X A] / [(1-T) Q A]

Baseline target: p* = 933.38 AUD/kg.

`finance` never imports `policy` (one-way dependency); a policy scenario is
passed in as a `config.PolicyScenario`.  Default = baseline (no policy).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

from .config import Config, PolicyScenario, POLICY_SCENARIOS, DEFAULT
from . import meb as _meb

BASELINE_POLICY = POLICY_SCENARIOS[1]


# ---------------------------------------------------------------------------
# CAPEX
# ---------------------------------------------------------------------------
def fci_topdown(cfg: Config = DEFAULT) -> float:
    """Six-tenths capacity scaling (CAPEX method 1). AUD."""
    cx, nm = cfg.capex, cfg.norm
    cap = cfg.meb.cap_prod / 1000.0                      # this plant t/yr
    return (cx.ref_capex_usd_m * 1_000_000
            * (cap / cx.ref_capacity_t) ** cx.scaling_exponent
            * nm.fx_usd_aud * cx.location_factor)


def fci_bottomup(cfg: Config = DEFAULT, equipment: Optional[Sequence[float]] = None) -> float:
    """Bottom-up Lang-factored estimate (CAPEX method 2). AUD."""
    pce = sum(equipment) if equipment else 0.0
    return pce * cfg.capex.lang_factor


def fci(cfg: Config = DEFAULT, equipment: Optional[Sequence[float]] = None) -> float:
    if cfg.capex.method == 2:
        return fci_bottomup(cfg, equipment)
    return fci_topdown(cfg)


def cepci_normalise(cost: float, cfg: Config = DEFAULT) -> float:
    """
    Escalate a pre-2026 literature capital cost to the valuation year using the
    NORM CEPCI factor.  (The default FCI anchor is already an implied 2024/2026
    figure, so this is applied only when importing external equipment costs.)
    """
    return cost * cfg.norm.cepci_fac


# ---------------------------------------------------------------------------
# WACC / discount factors
# ---------------------------------------------------------------------------
def wacc(cfg: Config = DEFAULT, wacc_case: int = 2) -> float:
    return {1: cfg.fin.wacc_low, 2: cfg.fin.wacc_base, 3: cfg.fin.wacc_high}[wacc_case]


def annuity_factor(r: float, n: int) -> float:
    return (1 - (1 + r) ** -n) / r


def eol_discount(r: float, n: int) -> float:
    return (1 + r) ** -n


# ---------------------------------------------------------------------------
# OPEX
# ---------------------------------------------------------------------------
def annual_variable_opex(cfg: Config = DEFAULT,
                         meb_result: Optional[_meb.MebResult] = None) -> Dict[str, float]:
    """Annual variable OPEX by line (AUD/yr).  Mirrors OPEX rows 5-15."""
    res = meb_result or _meb.run(cfg)
    Q = cfg.meb.cap_prod
    p = cfg.prices
    exp = res.export
    lines = {
        "electricity": exp["electricity_kwh"] * Q / 1000 * p.electricity.base,
        "steam":       exp["steam_kg"] * Q / 1000 * p.steam.base,
        "h2so4":       exp["h2so4_kg"] * Q / 1000 * p.h2so4.base,
        "naoh":        exp["naoh_kg"] * Q / 1000 * p.naoh.base,
        "cao":         exp["cao_kg"] * Q / 1000 * p.cao.base,
        "hcl":         exp["hcl_kg"] * Q / 1000 * p.hcl.base,
        "resin":       exp["resin_kg"] * Q / 1000 * 1000 * p.resin.base,  # $/kg
        "water":       exp["fresh_water_kg"] * Q / 1000 * p.water.base,
        "salty_disposal": exp["salty_reject_kg"] * Q / 1000 * p.salty_disposal.base,
        "residue_disposal": exp["solid_residue_kg"] * Q / 1000 * p.residue_disposal.base,
        "feedstock":   res.throughput_t * Q * p.feedstock.base,   # $0 by assumption
    }
    return lines


def annual_fixed_opex(cfg: Config = DEFAULT, fci_value: Optional[float] = None) -> Dict[str, float]:
    """Annual fixed OPEX (labour + maintenance + insurance). AUD/yr."""
    f = fci_value if fci_value is not None else fci(cfg)
    p = cfg.prices
    return {
        "labour": p.headcount.base * p.labour.base,
        "maintenance": p.maint_pct.base * f,
        "insurance": p.insurance_pct.base * f,
    }


def variable_opex_per_kg(cfg: Config = DEFAULT,
                         meb_result: Optional[_meb.MebResult] = None) -> float:
    """Variable OPEX per kg Ga (used by upcost.reconcile)."""
    return sum(annual_variable_opex(cfg, meb_result).values()) / cfg.meb.cap_prod


# ---------------------------------------------------------------------------
# Depreciation
# ---------------------------------------------------------------------------
def depreciation_schedule(cfg: Config, fci_value: float) -> Dict[str, List[float]]:
    """Return SL and DV annual depreciation over `life` years."""
    n, f = cfg.fin.life, fci_value
    sl = [f / n] * n
    dv, wdv = [], f
    rate = cfg.fin.dv_rate
    for t in range(1, n + 1):
        d = wdv if t == n else wdv * rate          # write off remaining WDV in final year
        dv.append(d)
        wdv -= d
    return {"SL": sl, "DV": dv}


def deprec_pv(cfg: Config, fci_value: float, r: float) -> float:
    """PV of the *selected* depreciation method at real WACC r."""
    sched = depreciation_schedule(cfg, fci_value)
    dep = sched["SL"] if cfg.fin.deprec_method == 1 else sched["DV"]
    return sum(d * (1 + r) ** -(t + 1) for t, d in enumerate(dep))


# ---------------------------------------------------------------------------
# Aggregate result
# ---------------------------------------------------------------------------
@dataclass
class FinanceResult:
    fci: float
    working_capital: float
    tci: float
    opex_variable: float
    opex_fixed: float
    opex_total: float
    wacc: float
    annuity: float
    eol_discount: float
    pv_depreciation: float
    lcop_pretax: float
    mvp: float                       # p*  (headline)
    cost_stack: Dict[str, float]
    policy_offset: float
    Q: float

    def summary(self) -> Dict[str, float]:
        return {
            "fci": self.fci, "working_capital": self.working_capital, "tci": self.tci,
            "opex_variable": self.opex_variable, "opex_fixed": self.opex_fixed,
            "opex_total": self.opex_total, "wacc": self.wacc,
            "pv_depreciation": self.pv_depreciation,
            "lcop_pretax": self.lcop_pretax, "mvp": self.mvp,
        }


def run(cfg: Config = DEFAULT,
        policy: PolicyScenario = BASELINE_POLICY,
        meb_result: Optional[_meb.MebResult] = None,
        equipment: Optional[Sequence[float]] = None) -> FinanceResult:
    """Full financial roll-up for a given policy scenario."""
    res = meb_result or _meb.run(cfg)
    fin = cfg.fin
    Q = cfg.meb.cap_prod
    T = fin.tax_rate
    c = policy.opex_offset
    r = wacc(cfg, policy.wacc_case)
    A = annuity_factor(r, fin.life)
    vn = eol_discount(r, fin.life)

    f = fci(cfg, equipment)
    var = annual_variable_opex(cfg, res)
    var_sub = sum(var.values())
    fixed = annual_fixed_opex(cfg, f)
    fixed_sub = sum(fixed.values())
    X = var_sub + fixed_sub                                 # OPEX_TOT
    WC = cfg.capex.wc_pct * X
    TCI = f + WC
    S = fin.salvage
    pvdep = deprec_pv(cfg, f, r)

    lcop = (f + WC * (1 - vn) - S * vn + (1 - c) * X * A) / (Q * A)
    mvp = (f + WC * (1 - vn) - S * vn - T * pvdep + (1 - T - c) * X * A) / ((1 - T) * Q * A)

    # pre-tax cost stack (AUD per kg), LCOP sheet rows 29-44
    stack = {"capital_charge": (f + WC * (1 - vn) - S * vn) / (A * Q)}
    for k, v in var.items():
        stack[k] = v / Q
    stack["labour"] = fixed["labour"] / Q
    stack["maintenance"] = fixed["maintenance"] / Q
    stack["insurance"] = fixed["insurance"] / Q
    stack["policy_offset"] = -c * X / Q

    return FinanceResult(
        fci=f, working_capital=WC, tci=TCI,
        opex_variable=var_sub, opex_fixed=fixed_sub, opex_total=X,
        wacc=r, annuity=A, eol_discount=vn, pv_depreciation=pvdep,
        lcop_pretax=lcop, mvp=mvp, cost_stack=stack, policy_offset=c, Q=Q)


def npv_at_price(price: float, cfg: Config = DEFAULT,
                 policy: PolicyScenario = BASELINE_POLICY,
                 meb_result: Optional[_meb.MebResult] = None) -> float:
    """
    Real post-tax NPV at a given sale price (CASHFLOW check).  Should read ~0
    when price == mvp.  Verifies the closed-form p* identity.
    """
    fr = run(cfg, policy, meb_result)
    fin = cfg.fin
    Q, T, c = fr.Q, fin.tax_rate, policy.opex_offset
    r, A, vn = fr.wacc, fr.annuity, fr.eol_discount
    sched = depreciation_schedule(cfg, fr.fci)
    dep = sched["SL"] if fin.deprec_method == 1 else sched["DV"]
    npv = -fr.fci - fr.working_capital
    for t in range(1, fin.life + 1):
        d = dep[t - 1]
        ebit = price * Q - fr.opex_total - d
        after_tax = ebit * (1 - T) + d + c * fr.opex_total
        npv += after_tax * (1 + r) ** -t
    npv += (fr.working_capital + fin.salvage) * vn
    return npv


__all__ = ["fci_topdown", "fci_bottomup", "fci", "cepci_normalise", "wacc",
           "annuity_factor", "eol_discount", "annual_variable_opex",
           "annual_fixed_opex", "variable_opex_per_kg", "depreciation_schedule",
           "deprec_pv", "FinanceResult", "run", "npv_at_price", "BASELINE_POLICY"]
