"""
openga.montecarlo
=================
Monte Carlo uncertainty on the minimum viable price p* (WP4 MC sheet).

Correlated triangular draws over the key uncertain inputs (unit prices, FX and
feed Ga concentration) via a Gaussian copula, propagated through the full
finance model to produce a distribution of p*.

The deterministic single-variable analogue lives in `openga.sensitivity`
(same parameter set, one-at-a-time sweeps).
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from statistics import NormalDist
from typing import Dict, List, Optional, Sequence

import numpy as np

from .config import Config, PriceRange, DEFAULT
from . import finance as _fin

_N = NormalDist()

# variables drawn as triangular(low, base, high).  Each maps to a config setter.
_PRICE_VARS = ["electricity", "steam", "h2so4", "naoh", "cao", "hcl", "resin",
               "water", "salty_disposal", "residue_disposal"]
# plus: fx (AUD/USD), feed (mg/L Ga), wacc (real)
_EXTRA_VARS = ["fx", "feed", "wacc"]
VARS: List[str] = _PRICE_VARS + _EXTRA_VARS

# default correlation: chemical/energy prices mildly co-move (supply shocks);
# FX independent; feed & WACC independent.  Override with `correlation=`.
_DEFAULT_RHO = 0.30


def _triangular_inv(u: float, low: float, mode: float, high: float) -> float:
    if high == low:
        return low
    c = (mode - low) / (high - low)
    if u < c:
        return low + (u * (high - low) * (mode - low)) ** 0.5
    return high - ((1 - u) * (high - low) * (high - mode)) ** 0.5


def _bounds(cfg: Config, var: str):
    if var in _PRICE_VARS:
        pr: PriceRange = getattr(cfg.prices, var)
        return pr.low, pr.base, pr.high
    if var == "fx":
        b = cfg.norm.fx_usd_aud
        return b * 0.9, b, b * 1.1
    if var == "feed":
        return 60.0, cfg.meb.ga_feed, 160.0
    if var == "wacc":
        return cfg.fin.wacc_low, cfg.fin.wacc_base, cfg.fin.wacc_high
    raise KeyError(var)


def _apply(cfg: Config, draws: Dict[str, float]) -> Config:
    prices = cfg.prices
    price_over = {}
    for v in _PRICE_VARS:
        pr: PriceRange = getattr(prices, v)
        price_over[v] = replace(pr, base=draws[v])
    cfg = cfg.with_(prices=replace(prices, **price_over))
    cfg = cfg.with_(norm=replace(cfg.norm, fx_usd_aud=draws["fx"]))
    cfg = cfg.with_(meb=replace(cfg.meb, ga_feed=draws["feed"]))
    cfg = cfg.with_(fin=replace(cfg.fin, wacc_base=draws["wacc"]))
    return cfg


def _correlation_matrix(vars_: Sequence[str], rho: float,
                        override: Optional[np.ndarray]) -> np.ndarray:
    if override is not None:
        return np.asarray(override, dtype=float)
    n = len(vars_)
    m = np.eye(n)
    # correlate the chemical/energy price block only
    idx = [i for i, v in enumerate(vars_) if v in _PRICE_VARS]
    for i in idx:
        for j in idx:
            if i != j:
                m[i, j] = rho
    return m


@dataclass
class MonteCarloResult:
    samples: np.ndarray            # p* per trial
    trials: int

    def percentile(self, q: float) -> float:
        return float(np.percentile(self.samples, q))

    def summary(self) -> Dict[str, float]:
        s = self.samples
        return {
            "mean": float(s.mean()), "std": float(s.std(ddof=1)),
            "p10": self.percentile(10), "p50": self.percentile(50),
            "p90": self.percentile(90), "min": float(s.min()), "max": float(s.max()),
        }


def run(cfg: Config = DEFAULT, trials: int = 2000, seed: Optional[int] = 42,
        rho: float = _DEFAULT_RHO,
        correlation: Optional[np.ndarray] = None) -> MonteCarloResult:
    """Draw `trials` correlated scenarios and return the p* distribution."""
    rng = np.random.default_rng(seed)
    corr = _correlation_matrix(VARS, rho, correlation)
    # correlated standard normals -> uniforms (Gaussian copula)
    z = rng.multivariate_normal(np.zeros(len(VARS)), corr, size=trials)
    u = np.vectorize(_N.cdf)(z)

    bounds = {v: _bounds(cfg, v) for v in VARS}
    out = np.empty(trials)
    for k in range(trials):
        draws = {v: _triangular_inv(u[k, i], *bounds[v]) for i, v in enumerate(VARS)}
        out[k] = _fin.run(_apply(cfg, draws)).mvp
    return MonteCarloResult(out, trials)


__all__ = ["VARS", "MonteCarloResult", "run"]
