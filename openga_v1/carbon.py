"""
openga_v1.carbon
================

Emissions per kilogram of 4N gallium, by unit operation, on the allocation
register. Three categories kept apart: scope 1, scope 2 and selected upstream
or embodied.

Boundary
--------
INSIDE   onsite fuel combustion (scope 1); purchased electricity and purchased
         steam (scope 2); upstream and embodied emissions for grid network
         losses, upstream gas supply, renewable and battery manufacturing, and
         the purchased chemicals, water and waste the MEB quantifies.

OUTSIDE  plant construction and equipment manufacture, decommissioning,
         employee transport, fugitive process emissions other than the fuel
         supply chain, reagent and residue transport, refrigerants, land use
         change, and every impact category other than global warming.

This is a SCREENING INVENTORY, not a complete product LCA.

The Bayer liquor carries zero upstream burden by cut-off: the slipstream is
drawn from and returned to a refinery circuit that would run anyway. That is
the largest boundary decision here. An economic or mass allocation would load
part of the alumina footprint onto the gallium and it would not be small. No
avoided-burden credit is taken for the sodium sulfate returned to the host.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .allocation import AllocationResult
from .config import UNIT_OPS
from .energy import EnergyResult

MATERIAL_EF_KEYS = {
    "h2so4": "EF_H2SO4",
    "naoh": "EF_NAOH",
    "cao": "EF_CAO",
    "hcl": "EF_HCL",
    "resin": "EF_RESIN",
    "water": "EF_WATER",
    "reject": "EF_REJECT",
    "solid": "EF_SOLID",
    "liquor": "EF_FEED",
}


@dataclass
class CarbonResult:
    by_up: dict[str, dict[str, float]] = field(default_factory=dict)
    scope1: float = 0.0
    scope2: float = 0.0
    upstream: float = 0.0
    total: float = 0.0
    scope12: float = 0.0
    annual_t_all: float = 0.0
    annual_t_s12: float = 0.0
    electricity_share: float = 0.0
    # 100% grid reference, computed independently
    ref_elec_ef: float = 0.0
    ref_elec_emissions: float = 0.0
    ref_total: float = 0.0
    non_electricity: float = 0.0
    reference_matches: bool = True
    independent_total: float = 0.0
    ties_back: bool = True


def run(p: dict, alloc: AllocationResult, en: EnergyResult, elec_kwh_kg: float) -> CarbonResult:
    r = CarbonResult()
    ef_steam = p["SteamLatent"] / p["BOILEFF"] / 1000.0 * p["EF_GAS"]

    for u, _ in UNIT_OPS:
        q = alloc.phys[u]
        s1 = q["electricity"] * en.mix_ef_s1
        s2 = q["electricity"] * en.mix_ef_s2 + q["steam"] * ef_steam
        up = q["electricity"] * en.mix_ef_up
        up += sum(q[k] * p[key] for k, key in MATERIAL_EF_KEYS.items())
        r.by_up[u] = {"electricity_kwh": q["electricity"], "scope1": s1, "scope2": s2,
                      "upstream": up, "total": s1 + s2 + up}

    r.scope1 = sum(v["scope1"] for v in r.by_up.values())
    r.scope2 = sum(v["scope2"] for v in r.by_up.values())
    r.upstream = sum(v["upstream"] for v in r.by_up.values())
    r.total = r.scope1 + r.scope2 + r.upstream
    r.scope12 = r.scope1 + r.scope2
    r.annual_t_all = r.total * p["CapProd"] / 1000.0
    r.annual_t_s12 = r.scope12 * p["CapProd"] / 1000.0

    elec_em = elec_kwh_kg * en.mix_ef_total
    r.electricity_share = elec_em / r.total if r.total else 0.0
    r.non_electricity = r.total - elec_em

    # --- 100% grid reference, computed from the grid route only. It never
    #     reads the selected mix, so a 100% grid selection must reproduce it.
    r.ref_elec_ef = en.grid_ef_total
    r.ref_elec_emissions = elec_kwh_kg * r.ref_elec_ef
    r.ref_total = r.ref_elec_emissions + r.non_electricity
    if p["MIX_GRID"] == 1.0:
        r.reference_matches = abs(r.total - r.ref_total) < 1e-9

    # --- independent recomputation from plant totals, touching no allocation
    t = alloc.plant_totals
    r.independent_total = (
        t["electricity"] * en.mix_ef_total
        + t["steam"] * ef_steam
        + sum(t[k] * p[key] for k, key in MATERIAL_EF_KEYS.items()))
    r.ties_back = abs(r.independent_total - r.total) < 1e-6
    return r
