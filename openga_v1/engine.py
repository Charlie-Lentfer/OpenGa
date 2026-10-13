"""
openga_v1.engine
================

One function, ``run(ModelInputs) -> Results``, that walks the whole model in
dependency order and hands back everything the UI needs.

Order matters and there is no iteration anywhere:

    MEB -> equipment -> variable OPEX -> CAPEX -> fixed OPEX -> working capital
        -> energy mix -> policy -> finance -> allocation -> carbon

Working capital is a fraction of operating cost and maintenance is a fraction
of ISBL, which looks circular but is not: variable cost does not depend on
ISBL, so the chain resolves in one pass.

The blended electricity price is built only from the route assumptions and
never reads the active price, so switching the financial connection on cannot
create a loop.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import allocation, capex, carbon, energy, equipment, finance, meb, opex, policy
from .config import (LEGACY_POLICY_SCENARIOS, UNIT_OPS, ModelInputs,
                     default_policy_packages, get_resin_preset)
from .streams import build_streams


@dataclass
class Results:
    inputs: ModelInputs = None
    params: dict = field(default_factory=dict)
    meb: meb.MEBResult = None
    equipment: equipment.EquipResult = None
    capex: capex.CapexResult = None
    opex: opex.OpexResult = None
    energy: energy.EnergyResult = None
    policy: policy.PolicyResult = None
    finance: finance.FinanceResult = None
    allocation: allocation.AllocationResult = None
    carbon: carbon.CarbonResult = None
    cost_by_up: dict = field(default_factory=dict)
    resin: object = None
    warnings: list[str] = field(default_factory=list)
    streams: dict = field(default_factory=dict)

    # convenience
    @property
    def lcop(self) -> float:
        return self.finance.production_cost_per_kg

    @property
    def pstar(self) -> float:
        return self.finance.pstar


def run(mi: ModelInputs) -> Results:
    p = mi.resolved()
    cfg = mi.cfg
    res = Results(inputs=mi, params=p, resin=get_resin_preset(cfg.resin_preset))

    # 1. physical model
    res.meb = m = meb.run(p, energy_mode=cfg.energy_mode)
    res.streams = build_streams(p, m)
    res.equipment = eq = equipment.run(p, m)

    # 2. energy mix -> the electricity price everything downstream pays
    res.energy = en = energy.run(p, m.elec_kwh_kg)
    elec_price = en.active_price

    # 3. variable cost (independent of ISBL), then capital, then fixed cost
    _var, _q, var_total = opex.variable_only(p, m, elec_price)
    labour = p["N_LABOUR"] * p["P_LABOUR"]

    def opex_for(isbl: float) -> float:
        maint = isbl * p["F_MAINT"]
        ins = isbl * p["F_INS"]
        over = (labour + maint) * p["F_OVER"]
        return var_total + labour + maint + ins + over

    # CAPEX needs an OPEX total only for working capital, and working capital
    # does not feed ISBL, so one pass with a provisional OPEX is exact.
    cx0 = capex.run(p, eq, 0.0, cfg.capex_mode, cfg.capex_user, cfg.capex_stage, m.liquor_m3_h)
    opex_total = opex_for(cx0.isbl_aud)
    res.capex = cx = capex.run(p, eq, opex_total, cfg.capex_mode,
                               cfg.capex_user, cfg.capex_stage, m.liquor_m3_h)
    res.opex = ox = opex.run(p, m, cx.isbl_aud, elec_price)

    # 4. policy
    if cfg.policy_model == "v31":
        pkgs = default_policy_packages(p)
        pkg = next(k for k in pkgs if k.id == cfg.policy_package)
        elig = policy.eligible_opex(p, ox.variable, ox.fixed)
        res.policy = pol = policy.run_v31(p, pkg, cx.fci_aud, cx.working_capital_aud,
                                          ox.total, elig)
    else:
        res.policy = pol = policy.run_legacy(p, cfg.legacy_policy, ox.total)

    # 5. finance
    res.finance = fin = finance.run(p, cx.fci_aud, cx.working_capital_aud, ox.total, pol.value)

    # 6. allocation, cost and carbon by unit operation
    res.allocation = al = allocation.run(p, m, cx.isbl_by_up)
    res.cost_by_up = allocation.cost_by_up(p, al, ox.fixed_total,
                                           fin.capital_charge_per_kg, elec_price)
    res.carbon = carbon.run(p, al, en, m.elec_kwh_kg)

    # 7. warnings the user must not miss
    w = res.warnings
    if not en.valid:
        w.append(en.invalid_reason)
    if not en.rte_valid or not en.geneff_valid:
        w.extend(en.notes)
    if not al.closes:
        w.append(f"Allocation does not close: worst residual {al.max_residual:.3e}. "
                 "The per-unit charts are not a decomposition of the totals.")
    if not res.carbon.ties_back:
        w.append("Carbon by unit operation does not agree with the independent recomputation.")
    if eq.out_of_range and cfg.capex_mode == "bottom_up":
        w.append(f"{eq.out_of_range} equipment item(s) are sized outside their correlation's "
                 "published range. The correlation is being extrapolated.")
    if cfg.energy_mode == "legacy_wp3":
        w.append("Legacy WP3 energy mode is active. Electricity is an allocation scaled from "
                 "Luo et al., not a duty calculation, and cannot be reconciled with pumping "
                 "physics at any plausible head.")
    if cfg.capex_mode == "per_stage" and cx.isbl_aud <= 0:
        w.append("Per-stage CAPEX is selected and every stage is zero, so all capital-derived "
                 "figures are zero.")
    w.extend(m.notes)
    return res


def scenario_sweep(mi: ModelInputs) -> list[dict]:
    """Run all four v3.1 policy packages on one set of physical assumptions."""
    out = []
    base = run(mi)
    for pkg_id in (1, 2, 3, 4):
        cfg = _clone_cfg(mi.cfg, policy_package=pkg_id, policy_model="v31")
        r = run(ModelInputs(params=mi.params, cfg=cfg))
        out.append({
            "id": pkg_id,
            "name": r.policy.label,
            "pstar": r.pstar,
            "pstar_usd": r.finance.pstar_usd,
            "lcop": r.lcop,
            "wacc_real": r.finance.real_wacc,
            "grant": r.policy.value.grant_gross,
            "supported_debt": r.policy.supported_debt,
            "pv_concession": r.policy.value.pv_concession,
            "cmpti_annual": r.policy.value.cmpti_annual,
            "pv_cmpti": r.policy.value.pv_cmpti,
        })
    ref = out[0]["pstar"]
    for row in out:
        row["reduction"] = ref - row["pstar"]
        row["reduction_pct"] = (ref - row["pstar"]) / ref if ref else 0.0
    return out


def _clone_cfg(cfg, **kw):
    import dataclasses
    return dataclasses.replace(cfg, **kw)
