"""
openga_v1.allocation
====================

The single allocation register. Cost per unit operation and carbon per unit
operation both read this, so they cannot drift apart.

Allocation changes attribution, never totals. Every column reconciles to the
plant figure it came from and ``residuals()`` proves it.

Conventions, stated rather than buried
--------------------------------------
* Sulfuric acid is charged to UP4, the acid make-up unit, not to UP5 where it
  is consumed.
* Resin MAKE-UP is charged to UP6, where the resin is replaced. The initial
  resin CHARGE stays capital at UP2.
* Liquor circuit pumping is split between UP1 and UP2 by ``AL_LIQ1``. That
  single typed fraction is the only allocation assumption in the model; the
  40 m head lumps take-off, filter press, ion exchange bed and return, and it
  cannot be split without a hydraulic model.
* Secondary pumping splits across UP3, UP5 and UP6 by the volumes each circuit
  moves. Ancillary electricity and all fixed cost split by installed-capital
  share. Raw water splits pro-rata across its four consuming duties.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .config import UNIT_OPS
from .meb import MEBResult

RESOURCES = [
    ("electricity", "Electricity", "kWh"),
    ("steam", "Steam", "kg"),
    ("h2so4", "H2SO4 98%", "kg"),
    ("naoh", "NaOH 100%", "kg"),
    ("cao", "CaO", "kg"),
    ("hcl", "HCl", "kg"),
    ("resin", "Resin make-up", "kg"),
    ("water", "Raw water", "kg"),
    ("reject", "Treatment reject", "kg"),
    ("solid", "Solid residue", "kg"),
    ("liquor", "Bayer liquor", "kg"),
]


@dataclass
class AllocationResult:
    """All quantities per kilogram of 4N gallium."""
    phys: dict[str, dict[str, float]] = field(default_factory=dict)   # up -> resource -> qty
    capital_share: dict[str, float] = field(default_factory=dict)
    plant_totals: dict[str, float] = field(default_factory=dict)
    allocated_totals: dict[str, float] = field(default_factory=dict)
    residuals: dict[str, float] = field(default_factory=dict)
    max_residual: float = 0.0
    closes: bool = True


def run(p: dict, m: MEBResult, isbl_by_up: dict[str, float]) -> AllocationResult:
    r = AllocationResult()
    ups = [u for u, _ in UNIT_OPS]
    C, H = p["CapProd"], p["OpHours"]

    # --- capital share (the basis for ancillary power and all fixed cost)
    tot_isbl = sum(isbl_by_up.get(u, 0.0) for u in ups)
    if tot_isbl > 0:
        r.capital_share = {u: isbl_by_up.get(u, 0.0) / tot_isbl for u in ups}
    else:
        r.capital_share = {u: 0.0 for u in ups}

    # --- electricity components, per kg Ga
    e_liq = m.kw_liquor * H / C
    e_sec = m.kw_secondary * H / C
    e_ew = m.kw_ew * H / C
    e_misc = m.elec_kwh_kg - e_liq - e_sec - e_ew

    sec_den = m.wash_m3_yr + m.elu_m3_yr + m.regen_m3_yr
    f_wash = m.wash_m3_yr / sec_den if sec_den else 0.0
    f_elu = m.elu_m3_yr / sec_den if sec_den else 0.0
    f_regen = m.regen_m3_yr / sec_den if sec_den else 0.0

    elec = {u: e_misc * r.capital_share[u] for u in ups}
    elec["UP1"] += e_liq * p["AL_LIQ1"]
    elec["UP2"] += e_liq * (1.0 - p["AL_LIQ1"])
    elec["UP3"] += e_sec * f_wash
    elec["UP5"] += e_sec * f_elu
    elec["UP6"] += e_sec * f_regen
    elec["UP10"] += e_ew

    # --- raw water, grossed up for reject then split by net demand share
    wnet = m.w_net_kg
    water = {u: 0.0 for u in ups}
    if wnet > 0:
        water["UP3"] = m.w_raw_kg * m.w_wash_kg / wnet
        water["UP5"] = m.w_raw_kg * m.w_elu_kg / wnet
        water["UP6"] = m.w_raw_kg * m.w_regen_kg / wnet
        water["UP9"] = m.w_raw_kg * m.w_makeup_kg / wnet

    solid_up9 = (m.al_cake * (p["MAl"] + 3 * p["MOH"]) / p["MAl"] + m.cao
                 + m.ga_cake - m.ga_elyte)

    zero = {k: 0.0 for k, _l, _u in RESOURCES}
    for u in ups:
        r.phys[u] = dict(zero)
        r.phys[u]["electricity"] = elec[u]
        r.phys[u]["water"] = water[u]
    r.phys["UP9"]["steam"] = m.steam_kg_kg
    r.phys["UP4"]["h2so4"] = m.h2so4_delivered          # convention: acid make-up unit
    r.phys["UP7"]["naoh"] = m.naoh_up7
    r.phys["UP9"]["naoh"] += m.naoh_up9
    r.phys["UP9"]["cao"] = m.cao
    r.phys["UP11"]["hcl"] = m.hcl
    r.phys["UP6"]["resin"] = m.resin_makeup             # convention: replaced at regeneration
    r.phys["UP4"]["reject"] = m.w_rej_kg
    r.phys["UP6"]["solid"] = m.resin_makeup
    r.phys["UP9"]["solid"] += solid_up9
    r.phys["UP1"]["liquor"] = m.liquor_kg_per_kg

    r.plant_totals = {
        "electricity": m.elec_kwh_kg,
        "steam": m.steam_kg_kg,
        "h2so4": m.h2so4_delivered,
        "naoh": m.naoh_total,
        "cao": m.cao,
        "hcl": m.hcl,
        "resin": m.resin_makeup,
        "water": m.w_raw_kg,
        "reject": m.w_rej_kg,
        "solid": m.solid_residue,
        "liquor": m.liquor_kg_per_kg,
    }
    r.allocated_totals = {k: sum(r.phys[u][k] for u in ups) for k, _l, _u in RESOURCES}
    r.residuals = {k: r.allocated_totals[k] - r.plant_totals[k] for k in r.plant_totals}
    r.residuals["capital_share"] = sum(r.capital_share.values()) - (1.0 if tot_isbl else 0.0)
    r.max_residual = max(abs(v) for v in r.residuals.values())
    r.closes = r.max_residual < 1e-9
    return r


def cost_by_up(p: dict, alloc: AllocationResult, opex_fixed_total: float,
               capital_charge_per_kg: float, elec_price: float) -> dict[str, dict[str, float]]:
    """Variable, fixed, cash and production cost per unit operation, AUD/kg Ga."""
    C = p["CapProd"]
    price = {
        "electricity": elec_price / 1000.0,
        "steam": p["P_STEAM"] / 1000.0,
        "h2so4": p["P_H2SO4"] / 1000.0,
        "naoh": p["P_NAOH"] / 1000.0,
        "cao": p["P_CAO"] / 1000.0,
        "hcl": p["P_HCL"] / 1000.0,
        "resin": p["P_RESIN"],
        "water": p["P_WATER"] / 1000.0,
        "reject": p["P_SALTY"] / 1000.0,
        "solid": p["P_SOLID"] / 1000.0,
        "liquor": p["P_FEED"] / 1000.0,
    }
    out: dict[str, dict[str, float]] = {}
    for u, _ in UNIT_OPS:
        var = sum(alloc.phys[u][k] * price[k] for k in price)
        fix = opex_fixed_total / C * alloc.capital_share[u]
        cap = capital_charge_per_kg * alloc.capital_share[u]
        out[u] = {"variable": var, "fixed": fix, "cash": var + fix,
                  "capital": cap, "production": var + fix + cap}
    return out
