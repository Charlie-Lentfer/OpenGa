"""
openga.sensitivity
==================
Deterministic sensitivity analysis (WP4 SENS + BREAKEVEN sheets).

- `tornado()`  : one-at-a-time low/base/high sweeps of the key drivers, ranked
                 by their swing in the minimum viable price p*.
- `breakeven_feed()` : MVP vs feed Ga concentration (50-250 mg/L), reproducing
                 the BREAKEVEN sheet.  Only throughput-scaled electricity
                 (UP1+UP2+UP3) rescales with 1/concentration; FCI, working
                 capital %, PV(depreciation) and non-electricity OPEX are HELD
                 CONSTANT -- so low-concentration MVPs are OPTIMISTIC on capital
                 (stated limitation; liquor-handling equipment is not rescaled).
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Callable, Dict, List, Optional, Tuple

from .config import Config, PriceRange, DEFAULT
from . import meb as _meb
from . import finance as _fin


def _mvp(cfg: Config, res: Optional[_meb.MebResult] = None) -> float:
    return _fin.run(cfg, meb_result=res).mvp


# ---------------------------------------------------------------------------
# Tornado (one-at-a-time)
# ---------------------------------------------------------------------------
def _set_fx(cfg: Config, val: float) -> Config:
    return cfg.with_(norm=replace(cfg.norm, fx_usd_aud=val))


def _set_feed(cfg: Config, val: float) -> Config:
    return cfg.with_(meb=replace(cfg.meb, ga_feed=val))


def _set_wacc(cfg: Config, val: float) -> Config:
    return cfg.with_(fin=replace(cfg.fin, wacc_base=val))


@dataclass
class TornadoBar:
    variable: str
    low_mvp: float
    high_mvp: float
    base_mvp: float

    @property
    def swing(self) -> float:
        return abs(self.high_mvp - self.low_mvp)


# driver -> (setter, low, high)   using PRICES low/high, FX +/-10%, feed 60-160, WACC low/high
def _default_drivers(cfg: Config) -> Dict[str, Tuple[Callable[[Config, float], Config], float, float]]:
    p = cfg.prices
    return {
        "Electricity price ($/MWh)": (lambda c, v: _set_price_val(c, "electricity", v), p.electricity.low, p.electricity.high),
        "NaOH price ($/t)":          (lambda c, v: _set_price_val(c, "naoh", v), p.naoh.low, p.naoh.high),
        "IX resin price ($/kg)":     (lambda c, v: _set_price_val(c, "resin", v), p.resin.low, p.resin.high),
        "H2SO4 price ($/t)":         (lambda c, v: _set_price_val(c, "h2so4", v), p.h2so4.low, p.h2so4.high),
        "Water price ($/kL)":        (lambda c, v: _set_price_val(c, "water", v), p.water.low, p.water.high),
        "FX (AUD/USD)":              (_set_fx, cfg.norm.fx_usd_aud * 0.9, cfg.norm.fx_usd_aud * 1.1),
        "Feed Ga (mg/L)":            (_set_feed, 60.0, 160.0),
        "Real WACC":                 (_set_wacc, cfg.fin.wacc_low, cfg.fin.wacc_high),
        "Maintenance (% FCI)":       (lambda c, v: _set_price_val(c, "maint_pct", v), p.maint_pct.low, p.maint_pct.high),
    }


def _set_price_val(cfg: Config, attr: str, val: float) -> Config:
    pr: PriceRange = getattr(cfg.prices, attr)
    new_prices = replace(cfg.prices, **{attr: replace(pr, base=val)})
    return cfg.with_(prices=new_prices)


def tornado(cfg: Config = DEFAULT) -> List[TornadoBar]:
    base = _mvp(cfg)
    bars: List[TornadoBar] = []
    for name, (setter, lo, hi) in _default_drivers(cfg).items():
        bars.append(TornadoBar(name, _mvp(setter(cfg, lo)), _mvp(setter(cfg, hi)), base))
    bars.sort(key=lambda b: b.swing, reverse=True)
    return bars


# ---------------------------------------------------------------------------
# Break-even feed concentration sweep
# ---------------------------------------------------------------------------
@dataclass
class BreakevenPoint:
    feed_mg_l: float
    total_electricity_kwh: float
    annual_opex: float
    mvp: float


def breakeven_feed(cfg: Config = DEFAULT,
                   concentrations: Optional[List[float]] = None) -> List[BreakevenPoint]:
    """
    Reproduce BREAKEVEN: MVP vs feed Ga concentration.  Capital held constant.
    """
    if concentrations is None:
        concentrations = list(range(50, 260, 10))          # 50..250 mg/L
    res = _meb.run(cfg)
    ref_conc = cfg.meb.ga_feed
    # throughput-scaled electricity at reference = UP1+UP2+UP3
    scaled_ref = sum(res.per_up[i].get("electricity_kwh", 0.0) for i in (0, 1, 2))
    total_ref = res.electricity_kwh
    fixed_elec = total_ref - scaled_ref

    fr = _fin.run(cfg, meb_result=res)
    fin = cfg.fin
    Q, T, c = fr.Q, fin.tax_rate, 0.0
    A, vn, pvdep, FCI, S = fr.annuity, fr.eol_discount, fr.pv_depreciation, fr.fci, fin.salvage
    opex_tot = fr.opex_total
    price_elec = cfg.prices.electricity.base

    pts: List[BreakevenPoint] = []
    for conc in concentrations:
        scaled = scaled_ref * ref_conc / conc
        total_elec = fixed_elec + scaled
        X = opex_tot + (total_elec - total_ref) / 1000 * price_elec * Q
        WC = cfg.capex.wc_pct * X
        mvp = (FCI + WC * (1 - vn) - S * vn - T * pvdep + (1 - T - c) * X * A) / ((1 - T) * Q * A)
        pts.append(BreakevenPoint(conc, total_elec, X, mvp))
    return pts


__all__ = ["TornadoBar", "tornado", "BreakevenPoint", "breakeven_feed"]
