"""
LCOP presentation helpers for the Streamlit app.

The app reports ONE cost: the levelised cost of production (LCOP), defined as
the constant real price per kilogram at which the plant earns its cost of
capital after company tax (NPV = 0). In the model this is ``finance.pstar``.

This module does no modelling of its own. It re-expresses the closed form in
``openga_v1.finance`` as four additive parts so the UI can explain the number:

    LCOP = operating cost
         + capital recovery          K / (Q.A)
         + company tax               T (K - PVDEP) / ((1-T) Q.A)
         - government support        (PV grant + PV CMPTI + PV concession) / ((1-T) Q.A)

with K = FCI + WC(1 - v^n) - salvage.v^n, A the annuity factor, Q annual
production and T the tax rate. ``bridge`` checks that the parts add back to
``finance.pstar`` and reports the residual.
"""

from __future__ import annotations

import dataclasses

from openga_v1 import config, engine
from openga_v1.analysis import DEFAULT_ASSAYS
from openga_v1.config import UNIT_OPS, ModelInputs


def bridge(R) -> dict:
    f, p, cx, v = R.finance, R.params, R.capex, R.policy.value
    T, Q, A = p["TAXR"], p["CapProd"], f.annuity
    K = cx.fci_aud + cx.working_capital_aud * (1 - f.vn) - p["SALV"] * f.vn
    d = (1 - T) * Q * A
    keep = 1.0 - v.opex_offset          # legacy WP4 OPEX offset; zero under v3.1
    out = {
        "variable": R.opex.variable_total / Q * keep,
        "fixed": R.opex.fixed_total / Q * keep,
        "operating": f.cash_cost_per_kg,
        "capital": K / (Q * A) if Q * A else 0.0,
        "tax": T * (K - f.pv_depreciation) / d if d else 0.0,
        "grant": v.pv_grant / d if d else 0.0,
        "cmpti": v.pv_cmpti / d if d else 0.0,
        "concession": v.pv_concession / d if d else 0.0,
        "lcop": f.pstar,
    }
    out["support"] = out["grant"] + out["cmpti"] + out["concession"]
    out["sum"] = out["operating"] + out["capital"] + out["tax"] - out["support"]
    out["residual"] = out["lcop"] - out["sum"]
    return out


def policy_runs(mi: ModelInputs) -> list[dict]:
    """Every policy setting of the active policy model on one set of inputs."""
    cfg = mi.cfg
    if cfg.policy_model == "v31":
        items = [(k.id, k.name) for k in config.default_policy_packages(mi.resolved())]
        field = "policy_package"
    else:
        items = [(s.id, s.name) for s in config.LEGACY_POLICY_SCENARIOS]
        field = "legacy_policy"
    runs = []
    for pid, name in items:
        c = dataclasses.replace(cfg, **{field: pid})
        runs.append({"id": pid, "name": name,
                     "R": engine.run(ModelInputs(params=mi.params, cfg=c)),
                     "cfg": c})
    return runs


def assay_by_policy(mi: ModelInputs, runs: list[dict], assays=None) -> tuple[list[dict], list[str]]:
    """LCOP against feed assay for each policy setting. A setting whose curve is
    identical to an earlier one is dropped and named in the second return value."""
    assays = assays or DEFAULT_ASSAYS
    series, dropped = {}, []
    for run in runs:
        pts = []
        for a in assays:
            m = mi.with_overrides({"GaFeed": float(a)})
            r = engine.run(ModelInputs(params=m.params, cfg=run["cfg"]))
            pts.append(r.pstar)
        dup = next((n for n, s in series.items()
                    if all(abs(x - y) < 1e-6 for x, y in zip(s, pts))), None)
        if dup:
            dropped.append(f"{run['name']} matches {dup}")
        else:
            series[run["name"]] = pts
    rows = [{"assay_mgL": float(a), "Policy": name, "LCOP": vals[i]}
            for name, vals in series.items() for i, a in enumerate(assays)]
    return rows, dropped


def by_unit(R, b: dict) -> list[dict]:
    """LCOP split by unit operation. Variable and fixed operating cost come
    straight from the allocation; capital recovery, company tax and support are
    carried together on the same installed-capital share, so the columns add to
    the headline LCOP."""
    cap_total = R.finance.capital_charge_per_kg
    kappa = (b["lcop"] - b["operating"]) / cap_total if cap_total else 0.0
    keep = 1.0 - R.policy.value.opex_offset
    rows = []
    for u, _name in UNIT_OPS:
        c = R.cost_by_up[u]
        rows.append({"unit": u,
                     "Variable operating": c["variable"] * keep,
                     "Fixed operating": c["fixed"] * keep,
                     "Capital recovery": c["capital"] * kappa})
    return rows
