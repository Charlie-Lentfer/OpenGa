"""
openga.cli
==========
Command-line entry point for each backend module (reproducibility-release
pattern).  Usage:

    python -m openga.cli meb
    python -m openga.cli carbon
    python -m openga.cli finance [--policy 1|2|3]
    python -m openga.cli policy
    python -m openga.cli validation
    python -m openga.cli breakeven
    python -m openga.cli montecarlo [--trials 2000] [--seed 42]
    python -m openga.cli all
"""
from __future__ import annotations

import argparse
import json

from .config import DEFAULT
from . import meb, carbon, upcost, finance, policy, validation, sensitivity, montecarlo


def _p(title, d):
    print(f"\n=== {title} ===")
    print(json.dumps({k: (round(v, 6) if isinstance(v, float) else v)
                      for k, v in d.items()}, indent=2))


def cmd_meb(a):
    _p("MEB (per kg 4N Ga)", meb.run(DEFAULT).summary())


def cmd_carbon(a):
    _p("CARBON (kg CO2e/kg, PLACEHOLDER EFs)", carbon.run(DEFAULT).summary())


def cmd_upcost(a):
    _p("UPCOST (AUD/kg, per UP)", upcost.run(DEFAULT).summary())


def cmd_finance(a):
    sel = getattr(a, "policy", 1)
    _p(f"FINANCE (policy {sel})", finance.run(DEFAULT, policy.scenario(sel)).summary())


def cmd_policy(a):
    for s in (1, 2, 3):
        r = policy.run(s)
        print(f"[{s}] {r.scenario.name:34s} p* = {r.mvp:8.2f} AUD/kg   "
              f"floor: {r.scenario.price_floor}")
    print("\n" + policy.price_floor_status())


def cmd_validation(a):
    w = validation.wesselkaemper(DEFAULT)
    for t in w.tests:
        print(f"{t.status:6s} {t.name:38s} {t.engine:8.2f} vs {t.target:8.2f} "
              f"({t.deviation*100:+.2f}%, tol {t.tolerance*100:.0f}%)")


def cmd_breakeven(a):
    print("feed_mg/L   total_elec_kWh   MVP_AUD/kg")
    for p in sensitivity.breakeven_feed(DEFAULT):
        print(f"{p.feed_mg_l:8.0f}   {p.total_electricity_kwh:12.3f}   {p.mvp:10.2f}")


def cmd_montecarlo(a):
    r = montecarlo.run(DEFAULT, trials=a.trials, seed=a.seed)
    _p(f"MONTE CARLO p* ({a.trials} trials)", r.summary())


def cmd_all(a):
    cmd_meb(a); cmd_carbon(a); cmd_upcost(a)
    cmd_finance(a); cmd_policy(a); cmd_validation(a)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="openga")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("meb", "carbon", "upcost", "policy", "validation", "breakeven", "all"):
        sub.add_parser(name)
    f = sub.add_parser("finance"); f.add_argument("--policy", type=int, default=1, choices=[1, 2, 3])
    m = sub.add_parser("montecarlo")
    m.add_argument("--trials", type=int, default=2000); m.add_argument("--seed", type=int, default=42)
    a = ap.parse_args(argv)
    globals()[f"cmd_{a.cmd}"](a)


if __name__ == "__main__":
    main()
