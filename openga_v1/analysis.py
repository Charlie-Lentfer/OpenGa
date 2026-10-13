"""
openga_v1.analysis
==================

Cost against feed assay, one-at-a-time sensitivity, and a triangular Monte
Carlo on p*.

All three re-run the complete model rather than a fitted surrogate. The
workbook used a regressed engine because Excel could not re-run itself; Python
can, so the approximation is dropped and the numbers are exact.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

from .config import ModelInputs
from .engine import run as run_engine


# ---------------------------------------------------------------------------
# Cost versus feed assay — the headline uncertainty
# ---------------------------------------------------------------------------

DEFAULT_ASSAYS = [40, 48, 55, 70, 85, 100, 140, 185, 240]


def assay_curve(mi: ModelInputs, assays=None) -> list[dict]:
    """No Australian refinery has published a gallium assay. This curve is the
    honest headline: a cost as a function of the number nobody has measured."""
    out = []
    for a in (assays or DEFAULT_ASSAYS):
        r = run_engine(mi.with_overrides({"GaFeed": float(a)}))
        out.append({
            "assay_mgL": float(a),
            "liquor_t_per_kg": r.meb.liquor_t_per_kg,
            "liquor_m3_h": r.meb.liquor_m3_h,
            "isbl": r.capex.isbl_aud,
            "fci": r.capex.fci_aud,
            "cash_cost": r.opex.cash_cost_per_kg,
            "production_cost": r.lcop,
            "pstar": r.pstar,
            "carbon": r.carbon.total,
            "electricity_kwh_kg": r.meb.elec_kwh_kg,
        })
    return out


# ---------------------------------------------------------------------------
# One-at-a-time sensitivity
# ---------------------------------------------------------------------------

@dataclass
class SensSpec:
    key: str
    label: str
    low: float
    high: float
    basis: str


def default_sensitivities(p: dict) -> list[SensSpec]:
    return [
        SensSpec("GaFeed", "Feed Ga assay (mg/L)", 48, 185,
                 "ICSOBA four-plant Bayer survey: 48 mg/L lowest, 185 mg/L at the "
                 "high-temperature refinery."),
        SensSpec("IXRec", "IX single-pass recovery (%)", 20, 60,
                 "R5 reports 31.7% on TY-CH550. Amidoxime resins claim up to 78% in the "
                 "laboratory."),
        SensSpec("CAPFAC", "Equipment-list completeness factor", 4, 8,
                 "The itemised list is incomplete; 6 reconciles it to the published "
                 "comparable."),
        SensSpec("CONTPCT", "Contingency", 0.10, 0.30,
                 "10% is the Towler minimum for a defined project. A first-of-a-kind plant "
                 "would carry more."),
        SensSpec("NaOH_UP9", "UP9 caustic dose (kg/kg)", p["NaOH_UP9"], 44.16,
                 "Base is the mechanistic electrolyte make-up. High is the Luo reported "
                 "gross dose."),
        SensSpec("P_NAOH", "NaOH price ($/t)", p["P_NAOH_LO"], p["P_NAOH_HI"], "Supplier quote range."),
        SensSpec("P_ELEC_BASE", "Electricity price ($/MWh)", p["P_ELEC_LO"], p["P_ELEC_HI"],
                 "Onsite PV+BESS to Australian industrial grid tariff (Lu et al. 2026)."),
        SensSpec("P_RESIN", "Resin price ($/kg)", p["P_RESIN_LO"], p["P_RESIN_HI"], "Vendor quote range."),
        SensSpec("P_LABOUR", "Labour rate ($/FTE-yr)", p["P_LABOUR_LO"], p["P_LABOUR_HI"],
                 "Australian process-industry loaded rate range."),
        SensSpec("N_LABOUR", "Operator headcount", p["N_LABOUR_LO"], p["N_LABOUR_HI"],
                 "Alcoa state about 20 direct operational jobs; 16-26 brackets it."),
        SensSpec("F_MAINT", "Maintenance (% of ISBL)", p["F_MAINT_LO"], p["F_MAINT_HI"],
                 "Textbook TEA factor range, 2-5% of ISBL."),
        SensSpec("RFR", "Risk-free rate", 0.035, 0.070,
                 "Ten-year AGS yield range. Drives the CAPM cost of equity and the debt "
                 "base rate together."),
    ]


def tornado(mi: ModelInputs, target: str = "pstar", specs=None) -> list[dict]:
    base = run_engine(mi)
    base_v = getattr(base, target) if target in ("pstar", "lcop") else base.carbon.total
    rows = []
    for s in (specs or default_sensitivities(mi.resolved())):
        lo = run_engine(mi.with_overrides({s.key: s.low}))
        hi = run_engine(mi.with_overrides({s.key: s.high}))
        lo_v = getattr(lo, target) if target in ("pstar", "lcop") else lo.carbon.total
        hi_v = getattr(hi, target) if target in ("pstar", "lcop") else hi.carbon.total
        rows.append({
            "key": s.key, "label": s.label, "basis": s.basis,
            "low_input": s.low, "high_input": s.high,
            "low": lo_v, "high": hi_v, "base": base_v,
            "swing": abs(hi_v - lo_v),
            "down": min(lo_v, hi_v) - base_v,
            "up": max(lo_v, hi_v) - base_v,
        })
    rows.sort(key=lambda r: r["swing"], reverse=True)
    return rows


# ---------------------------------------------------------------------------
# Monte Carlo
# ---------------------------------------------------------------------------

@dataclass
class MCSpec:
    key: str
    label: str
    low: float
    mode: float
    high: float
    basis: str = ""


def default_mc_specs(p: dict) -> list[MCSpec]:
    return [
        MCSpec("GaFeed", "Feed Ga assay (mg/L)", 48, p["GaFeed"], 185,
               "ICSOBA four-plant Bayer survey."),
        MCSpec("IXRec", "IX single-pass recovery (%)", 20, p["IXRec"], 60, "R5 / R12 range."),
        MCSpec("NaOH_UP9", "UP9 caustic dose (kg/kg)", p["NaOH_UP9"], p["NaOH_UP9"], 44.16,
               "Mechanistic make-up to the Luo reported gross dose."),
        MCSpec("CAPFAC", "Completeness factor", 4, p["CAPFAC"], 8, "Reconciliation range."),
        MCSpec("CONTPCT", "Contingency", p["CONTPCT"], p["CONTPCT"], 0.30, "Towler minimum upward."),
        MCSpec("RFR", "Risk-free rate", 0.035, p["RFR"], 0.070, "AGS yield range."),
        MCSpec("P_NAOH", "NaOH price ($/t)", p["P_NAOH_LO"], p["P_NAOH"], p["P_NAOH_HI"], ""),
        MCSpec("P_ELEC_BASE", "Electricity ($/MWh)", p["P_ELEC_LO"], p["P_ELEC_BASE"],
               p["P_ELEC_HI"], ""),
        MCSpec("P_RESIN", "Resin ($/kg)", p["P_RESIN_LO"], p["P_RESIN"], p["P_RESIN_HI"], ""),
        MCSpec("P_LABOUR", "Labour ($/FTE-yr)", p["P_LABOUR_LO"], p["P_LABOUR"],
               p["P_LABOUR_HI"], ""),
        MCSpec("N_LABOUR", "Headcount (FTE)", p["N_LABOUR_LO"], p["N_LABOUR"],
               p["N_LABOUR_HI"], ""),
        MCSpec("F_MAINT", "Maintenance (% ISBL)", p["F_MAINT_LO"], p["F_MAINT"],
               p["F_MAINT_HI"], ""),
    ]


def _triangular(rng: random.Random, lo: float, mode: float, hi: float) -> float:
    if hi <= lo:
        return lo
    mode = min(max(mode, lo), hi)
    return rng.triangular(lo, hi, mode)


def monte_carlo(mi: ModelInputs, trials: int = 1000, seed: int = 20260909,
                specs=None) -> dict:
    """Triangular distributions on twelve inputs, common draws across the four
    policy packages so the comparison is not contaminated by sampling noise."""
    p = mi.resolved()
    specs = specs or default_mc_specs(p)
    rng = random.Random(seed)
    lcop, pstar, carbon_v = [], [], []
    draws = []
    for _ in range(trials):
        d = {s.key: _triangular(rng, s.low, s.mode, s.high) for s in specs}
        draws.append(d)
        r = run_engine(mi.with_overrides(d))
        lcop.append(r.lcop)
        pstar.append(r.pstar)
        carbon_v.append(r.carbon.total)
    return {
        "specs": specs, "trials": trials, "seed": seed, "draws": draws,
        "lcop": lcop, "pstar": pstar, "carbon": carbon_v,
        "stats": {k: _stats(v) for k, v in
                  (("lcop", lcop), ("pstar", pstar), ("carbon", carbon_v))},
    }


def _stats(v: list[float]) -> dict:
    s = sorted(v)
    n = len(s)

    def pct(q):
        if n == 1:
            return s[0]
        i = q * (n - 1)
        lo, hi = int(math.floor(i)), int(math.ceil(i))
        return s[lo] + (s[hi] - s[lo]) * (i - lo)

    mean = sum(s) / n
    var = sum((x - mean) ** 2 for x in s) / (n - 1) if n > 1 else 0.0
    return {"mean": mean, "sd": var ** 0.5, "min": s[0], "max": s[-1],
            "p5": pct(0.05), "p10": pct(0.10), "p50": pct(0.50),
            "p90": pct(0.90), "p95": pct(0.95)}


def histogram(values: list[float], bins: int = 20) -> list[dict]:
    lo, hi = min(values), max(values)
    if hi <= lo:
        return [{"from": lo, "to": hi, "mid": lo, "count": len(values)}]
    w = (hi - lo) / bins
    counts = [0] * bins
    for v in values:
        i = min(bins - 1, int((v - lo) / w))
        counts[i] += 1
    return [{"from": lo + i * w, "to": lo + (i + 1) * w,
             "mid": lo + (i + 0.5) * w, "count": counts[i],
             "share": counts[i] / len(values)} for i in range(bins)]


def prob_below(values: list[float], threshold: float) -> float:
    return sum(1 for v in values if v < threshold) / len(values)
