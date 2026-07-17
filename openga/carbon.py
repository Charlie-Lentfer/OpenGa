"""
openga.carbon
=============
Per-unit-operation carbon accounting (WP3 CARBON / CARBON_EF sheets).

Emissions = MEB physical quantities (openga.meb) x scope-tagged emission
factors (config.CarbonEF).  Two reporting boundaries:

    Scope 1 + 2   : site electricity (S2, grid) + steam (S1, boiler)
    + embodied    : upstream chemicals, water and disposal

Grid decarbonisation applies to the Scope-2 slice only.

*** ALL EMISSION FACTORS ARE PLACEHOLDERS *** (config.CarbonEF, confidence
LOW-PLACEHOLDER).  Results are flagged as such; do not quote before sourcing.

Baseline targets (Australian scenario, placeholder EFs):
    S1+S2      ~ 77.73  kg CO2e/kg Ga
    +embodied  ~ 215.41 kg CO2e/kg Ga
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from .config import Config, CarbonEF, DEFAULT
from . import meb as _meb


PLACEHOLDER_WARNING = ("All emission factors are PLACEHOLDERS (config.CarbonEF, "
                       "confidence LOW). Source before thesis use.")


@dataclass
class UnitEmissions:
    name: str
    scope2_electricity: float
    scope1_steam: float
    embodied: float

    @property
    def s1_s2(self) -> float:
        return self.scope2_electricity + self.scope1_steam

    @property
    def total(self) -> float:
        return self.s1_s2 + self.embodied


@dataclass
class CarbonResult:
    per_up: List[UnitEmissions]
    scope2_total: float
    scope1_total: float
    embodied_total: float
    placeholder: bool = True

    @property
    def s1_s2_total(self) -> float:
        return self.scope1_total + self.scope2_total

    @property
    def total_with_embodied(self) -> float:
        return self.s1_s2_total + self.embodied_total

    def summary(self) -> Dict[str, float]:
        return {
            "scope2_electricity": self.scope2_total,
            "scope1_steam": self.scope1_total,
            "embodied": self.embodied_total,
            "s1_s2_total": self.s1_s2_total,
            "total_with_embodied": self.total_with_embodied,
        }


# map export column -> EF attribute for the embodied boundary
_EMBODIED_MAP = {
    "h2so4_kg": "h2so4",
    "naoh_kg": "naoh",
    "cao_kg": "cao",
    "hcl_kg": "hcl",
    "resin_kg": "resin",
    "fresh_water_kg": "fresh_water",
    "salty_reject_kg": "salty_reject",
    "solid_residue_kg": "solid_residue",
}


def _embodied(row: Dict[str, float], ef: CarbonEF) -> float:
    total = 0.0
    for col, ef_name in _EMBODIED_MAP.items():
        total += row.get(col, 0.0) * getattr(ef, ef_name).value
    return total


def run(cfg: Config = DEFAULT, meb_result: Optional[_meb.MebResult] = None,
        grid_ef: Optional[float] = None) -> CarbonResult:
    """
    Compute per-UP and total emissions.

    grid_ef : override the Scope-2 electricity factor (kg CO2e/kWh).  Defaults
              to the Australian site factor; pass config.ef.grid_elec_cn.value
              (0.58) to reproduce the Luo/China validation grid.
    """
    res = meb_result or _meb.run(cfg)
    ef = cfg.ef
    g = ef.grid_elec_au.value if grid_ef is None else grid_ef

    per_up: List[UnitEmissions] = []
    s2 = s1 = emb = 0.0
    for name, row in zip(_meb.UP_NAMES, res.per_up):
        e2 = row.get("electricity_kwh", 0.0) * g
        e1 = row.get("steam_kg", 0.0) * ef.steam.value
        eb = _embodied(row, ef)
        per_up.append(UnitEmissions(name, e2, e1, eb))
        s2 += e2
        s1 += e1
        emb += eb
    return CarbonResult(per_up, s2, s1, emb, placeholder=True)


@dataclass
class LuoValidation:
    computed_gwp: float          # kg CO2e/kg Ga using the China grid EF
    published_gwp: Optional[float]
    deviation: Optional[float]   # computed/published - 1
    status: str
    tolerance: float


def validate_luo(cfg: Config = DEFAULT, published_gwp: Optional[float] = None,
                 tolerance: float = 0.10) -> LuoValidation:
    """
    Reproduce WP3 CARBON!I6: recompute total GWP with the Chinese grid EF and
    the Luo inventory (requires scenario 1 + resin preset 4 for a true
    replication), then compare against a user-supplied published Luo GWP.

    computed = SUM(steam + embodied over all UPs) + total_electricity x EF_CN
    """
    china = cfg.ef.grid_elec_cn.value
    res = _meb.run(cfg)
    cr = run(cfg, res)
    computed = cr.scope1_total + cr.embodied_total + res.electricity_kwh * china
    if published_gwp in (None, 0):
        return LuoValidation(computed, None, None, "PENDING - enter Luo published GWP", tolerance)
    dev = computed / published_gwp - 1
    status = "PASS" if abs(dev) <= tolerance else "REVIEW"
    return LuoValidation(computed, published_gwp, dev, status, tolerance)


__all__ = ["UnitEmissions", "CarbonResult", "run", "LuoValidation",
           "validate_luo", "PLACEHOLDER_WARNING"]
