"""
openga.upcost
=============
Variable OPEX per unit operation (WP4 UPCOST sheet).

Per-UP variable cost = MEB quantity (openga.meb per-UP vector) x base unit
price (config.Prices).  Fixed OPEX (labour, maintenance, insurance) is a
single PLANT-LEVEL figure -- NOT allocated to unit operations, because there
is no non-arbitrary allocation basis (documented in UPCOST!A1).

Reconciliation invariant (asserted):
    sum(per-UP variable cost)  ==  finance variable-OPEX subtotal
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from .config import Config, Prices, DEFAULT
from . import meb as _meb

# export column -> (price attribute, per-unit divisor)
# divisor converts the MEB quantity (kg or kWh per kg Ga) into the price basis.
#   electricity: kWh -> MWh (/1000), price $/MWh
#   steam/acids/disposal: kg -> t (/1000), price $/t
#   resin: kg, price $/kg (divisor 1)
#   water: kg == L -> kL (/1000), price $/kL
_COST_MAP = {
    "electricity_kwh":   ("electricity", 1000.0),
    "steam_kg":          ("steam", 1000.0),
    "h2so4_kg":          ("h2so4", 1000.0),
    "naoh_kg":           ("naoh", 1000.0),
    "cao_kg":            ("cao", 1000.0),
    "hcl_kg":            ("hcl", 1000.0),
    "resin_kg":          ("resin", 1.0),
    "fresh_water_kg":    ("water", 1000.0),
    "salty_reject_kg":   ("salty_disposal", 1000.0),
    "solid_residue_kg":  ("residue_disposal", 1000.0),
}


@dataclass
class UnitCost:
    name: str
    lines: Dict[str, float]      # cost by item, AUD per kg Ga

    @property
    def total(self) -> float:
        return sum(self.lines.values())


@dataclass
class UpcostResult:
    per_up: List[UnitCost]
    variable_total_per_kg: float          # sum of per-UP variable cost

    def summary(self) -> Dict[str, float]:
        return {uc.name: uc.total for uc in self.per_up} | {
            "variable_total_per_kg": self.variable_total_per_kg}


def _price(prices: Prices, attr: str) -> float:
    return getattr(prices, attr).base


def run(cfg: Config = DEFAULT, meb_result: Optional[_meb.MebResult] = None) -> UpcostResult:
    res = meb_result or _meb.run(cfg)
    prices = cfg.prices
    per_up: List[UnitCost] = []
    grand = 0.0
    for name, row in zip(_meb.UP_NAMES, res.per_up):
        lines: Dict[str, float] = {}
        for col, (attr, div) in _COST_MAP.items():
            qty = row.get(col, 0.0)
            if qty:
                lines[attr] = qty * _price(prices, attr) / div
        uc = UnitCost(name, lines)
        per_up.append(uc)
        grand += uc.total
    return UpcostResult(per_up, grand)


def reconcile(cfg: Config = DEFAULT, meb_result: Optional[_meb.MebResult] = None,
              tol: float = 1e-6) -> float:
    """
    Assert sum(per-UP variable cost) == finance variable-OPEX subtotal.
    Returns the (signed) residual per kg Ga.
    """
    from . import finance as _fin
    res = meb_result or _meb.run(cfg)
    up = run(cfg, res)
    fin_var = _fin.variable_opex_per_kg(cfg, res)
    residual = up.variable_total_per_kg - fin_var
    assert abs(residual) <= tol, (
        f"UPCOST reconciliation failed: per-UP sum {up.variable_total_per_kg:.8f} "
        f"!= finance variable subtotal {fin_var:.8f} (residual {residual:.2e})")
    return residual


__all__ = ["UnitCost", "UpcostResult", "run", "reconcile"]
