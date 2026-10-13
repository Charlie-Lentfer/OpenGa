"""
openga_v1.opex
==============

Annual operating cost at capacity, in constant 2026 AUD.

Two passes are needed because working capital is a fraction of operating cost
while maintenance and insurance are fractions of ISBL. ``run`` takes ISBL as an
argument and the engine resolves the loop by computing variable cost first,
then ISBL, then fixed cost — never by iterating, so there is no circularity.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .meb import MEBResult


@dataclass
class OpexResult:
    variable: dict[str, float] = field(default_factory=dict)   # AUD/yr by line
    quantities: dict[str, tuple[float, str]] = field(default_factory=dict)
    fixed: dict[str, float] = field(default_factory=dict)
    variable_total: float = 0.0
    fixed_total: float = 0.0
    total: float = 0.0
    cash_cost_per_kg: float = 0.0
    stack_per_kg: dict[str, float] = field(default_factory=dict)
    electricity_price_used: float = 0.0


def variable_only(p: dict, m: MEBResult, elec_price: float) -> tuple[dict, dict, float]:
    C = p["CapProd"]
    q = {
        "Sulfuric acid (98% w/w)": (m.h2so4_delivered * C / 1000.0, "t/yr"),
        "Caustic soda (100% basis)": (m.naoh_total * C / 1000.0, "t/yr"),
        "Quicklime": (m.cao * C / 1000.0, "t/yr"),
        "Hydrochloric acid": (m.hcl * C / 1000.0, "t/yr"),
        "Ion exchange resin make-up": (m.resin_makeup_kg_yr, "kg/yr"),
        "Electricity": (m.elec_kwh_kg * C / 1000.0, "MWh/yr"),
        "Steam": (m.steam_kg_kg * C / 1000.0, "t/yr"),
        "Process water": (m.w_raw_m3_yr, "kL/yr"),
        "Bayer liquor feedstock": (m.liquor_t_yr, "t/yr"),
        "Water treatment reject disposal": (m.w_rej_m3_yr, "t/yr"),
        "Solid residue disposal": (m.solid_residue * C / 1000.0, "t/yr"),
    }
    price = {
        "Sulfuric acid (98% w/w)": p["P_H2SO4"],
        "Caustic soda (100% basis)": p["P_NAOH"],
        "Quicklime": p["P_CAO"],
        "Hydrochloric acid": p["P_HCL"],
        "Ion exchange resin make-up": p["P_RESIN"],
        "Electricity": elec_price,
        "Steam": p["P_STEAM"],
        "Process water": p["P_WATER"],
        "Bayer liquor feedstock": p["P_FEED"],
        "Water treatment reject disposal": p["P_SALTY"],
        "Solid residue disposal": p["P_SOLID"],
    }
    var = {k: q[k][0] * price[k] for k in q}
    return var, q, sum(var.values())


def run(p: dict, m: MEBResult, isbl_aud: float, elec_price: float) -> OpexResult:
    r = OpexResult(electricity_price_used=elec_price)
    r.variable, r.quantities, r.variable_total = variable_only(p, m, elec_price)

    labour = p["N_LABOUR"] * p["P_LABOUR"]
    maint = isbl_aud * p["F_MAINT"]
    ins = isbl_aud * p["F_INS"]
    over = (labour + maint) * p["F_OVER"]
    r.fixed = {
        "Operating labour": labour,
        "Maintenance": maint,
        "Insurance, rates and administration": ins,
        "Plant overhead": over,
    }
    r.fixed_total = sum(r.fixed.values())
    r.total = r.variable_total + r.fixed_total
    r.cash_cost_per_kg = r.total / p["CapProd"] if p["CapProd"] else 0.0

    C = p["CapProd"]
    r.stack_per_kg = {k: v / C for k, v in list(r.variable.items()) + list(r.fixed.items())}
    return r
