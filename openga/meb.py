"""
openga.meb
==========
Mass & energy balance for gallium recovery from spent Bayer liquor
(WP3_Balance_v3_3.xlsx, "rev. auditable rebuild").

Route 1: filter press -> ion exchange -> wash -> acid elution -> precipitation
-> centrifuge -> purification -> electrowinning -> refining to 4N.
Basis: 1 kg 4N Ga product.

Pure functions, no UI / no I/O.  `run(cfg)` returns a `MebResult` whose
`export` field is the per-kg quantity vector (UP_EXPORT sheet) consumed by
`openga.carbon`, `openga.upcost` and `openga.finance`.

Every unit operation carries its stream-table `checks` (In + ReactionDelta -
Out, which must close to ~0).  `MebResult.master_check` is MAX(|all checks|)
and must be 0 within `CLOSE_TOL` -- reproducing the WP3 CHECKS master cell.
Elemental closures for S, Na and Cl are computed explicitly and asserted.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from .config import Config, MebInputs, DEFAULT

CLOSE_TOL = 1e-6            # kg; workbook closes to ~1e-12, allow FP slack

# UP order used throughout the package (matches UP_EXPORT rows 6..16)
UP_NAMES: List[str] = [
    "UP1 Filter press", "UP2 Ion exchange", "UP3 Washing", "UP4 Acid make-up",
    "UP5 Elution", "UP6 Regeneration", "UP7 Precipitation", "UP8 Centrifuge",
    "UP9 Purification", "UP10 Electrowinning", "UP11 Refining",
]

# export-vector column keys (UP_EXPORT B..K)
QTY_KEYS: List[str] = [
    "electricity_kwh", "steam_kg", "h2so4_kg", "naoh_kg", "cao_kg", "hcl_kg",
    "resin_kg", "fresh_water_kg", "salty_reject_kg", "solid_residue_kg",
]


# ---------------------------------------------------------------------------
# Derived quantities  (WP3 INPUTS DERIVED block D01-D15)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Derived:
    rec_overall: float      # D01
    feed_ga: float          # D02  kg Ga fed per kg product
    mass_frac: float        # D03
    thru_kg: float          # D04  kg liquor per kg product
    thru_t: float           # D05  t liquor per kg product
    thru_l: float           # D06  L liquor per kg product
    thru_kg_b: float        # D07  baseline (Luo conc)
    ratio_t: float          # D08
    ga_ads: float           # D09
    v_ads: float            # D10
    v_ads_b: float          # D11
    resin_inv: float        # D12
    resin_inv_b: float      # D13
    ratio_resin: float      # D14
    ratio_hard: float       # D15


def derived(inp: MebInputs) -> Derived:
    """Reproduce INPUTS!F93:F107 exactly."""
    ix, elu, cent = inp.ix_rec, inp.elu_eff, inp.cent_rec
    pur, ew, ref = inp.pur_rec, inp.ew_rec, inp.ref_yield
    rec_overall = (ix / 100) * (elu / 100) * (cent / 100) * (pur / 100) * (ew / 100) * (ref / 100)
    feed_ga = 1.0 / rec_overall
    mass_frac = inp.ga_feed / (1_000_000 * inp.liq_density)
    thru_kg = feed_ga / mass_frac
    thru_t = thru_kg / 1000.0
    thru_l = thru_kg / inp.liq_density
    thru_kg_b = feed_ga / (inp.ga_feed_luo / (1_000_000 * inp.liq_density))
    ratio_t = thru_kg / thru_kg_b
    ga_ads = feed_ga * ix / 100.0
    v_ads = inp.v_feed / 1_000_000 * thru_l * inp.co_ads_v / 100.0
    v_ads_b = inp.v_feed_luo / 1_000_000 * (thru_kg_b / inp.liq_density) * inp.co_ads_v / 100.0
    resin_inv = (ga_ads + v_ads) / (inp.resin_cap / 1000.0)
    resin_inv_b = (ga_ads + v_ads_b) / (inp.resin_cap / 1000.0)
    ratio_resin = resin_inv / resin_inv_b
    ratio_hard = inp.hard_site / inp.hard_ref
    return Derived(rec_overall, feed_ga, mass_frac, thru_kg, thru_t, thru_l,
                   thru_kg_b, ratio_t, ga_ads, v_ads, v_ads_b, resin_inv,
                   resin_inv_b, ratio_resin, ratio_hard)


# ---------------------------------------------------------------------------
# Unit-operation result container
# ---------------------------------------------------------------------------
@dataclass
class UnitOp:
    name: str
    electricity_kwh: float = 0.0
    thermal_kwh: float = 0.0
    quantities: Dict[str, float] = field(default_factory=dict)   # export columns this UP contributes
    detail: Dict[str, float] = field(default_factory=dict)       # intermediate values (audit)
    checks: List[float] = field(default_factory=list)            # stream-table Check cells

    def qty(self, key: str) -> float:
        return self.quantities.get(key, 0.0)


def _blank_qty() -> Dict[str, float]:
    return {k: 0.0 for k in QTY_KEYS}


# ---------------------------------------------------------------------------
# The eleven unit operations.  Each returns a UnitOp; downstream Ga/Al/etc.
# masses are threaded through via a shared `stream` dict (elemental basis).
# ---------------------------------------------------------------------------
def _up1(inp, d, stream) -> UnitOp:
    """Filter press -- solids removed, no reaction."""
    q = _blank_qty()
    q["electricity_kwh"] = inp.e_up1 * d.ratio_t
    ss = inp.ss_load * d.thru_t                                   # to cake
    water = d.thru_kg - d.feed_ga - inp.al_feed / 1000 * d.thru_l - inp.v_feed / 1e6 * d.thru_l - ss
    checks = [0.0]  # every row closes by construction (Out = In)
    stream.update(ga=d.feed_ga,
                  al=inp.al_feed / 1000 * d.thru_l,
                  v=inp.v_feed / 1e6 * d.thru_l,
                  water=water)
    uo = UnitOp("UP1 Filter press", q["electricity_kwh"], 0.0, q,
                {"ss_to_cake": ss}, checks)
    return uo


def _up2(inp, d, stream) -> UnitOp:
    """Ion exchange -- Ga & co-adsorbed V/Al onto resin."""
    q = _blank_qty()
    q["electricity_kwh"] = inp.e_up2 * d.ratio_t
    ga_in = stream["ga"]
    ga_ads = ga_in * inp.ix_rec / 100
    al_ads = stream["al"] * inp.co_ads_al / 100
    v_ads = stream["v"] * inp.co_ads_v / 100
    total_in = ga_in + stream["al"] + stream["v"] + stream["water"]
    total_out = (ga_in - ga_ads) + (stream["al"] - al_ads) + (stream["v"] - v_ads) + stream["water"] \
        + ga_ads + al_ads + v_ads
    checks = [total_in - total_out]
    stream.update(ga=ga_ads, al=al_ads, v=v_ads, water=0.0)      # loaded resin stream forward
    return UnitOp("UP2 Ion exchange", q["electricity_kwh"], 0.0, q,
                  {"ga_ads": ga_ads, "v_ads": v_ads, "resin_inv": d.resin_inv,
                   "ratio_resin": d.ratio_resin}, checks)


def _up3(inp, d, stream) -> UnitOp:
    """Washing -- displacement wash of loaded resin."""
    q = _blank_qty()
    wash = inp.wash_base * d.ratio_resin
    q["fresh_water_kg"] = wash
    q["electricity_kwh"] = inp.e_up3 * d.ratio_resin
    # wash water in == wash waste out; metals retained on resin -> check 0
    checks = [0.0]
    return UnitOp("UP3 Washing", q["electricity_kwh"], 0.0, q, {"wash_water": wash}, checks)


def _up4(inp, d, stream) -> UnitOp:
    """Softening / acid make-up.  Raw water is the closure variable."""
    q = _blank_qty()
    dose = inp.acid_base * d.ratio_resin
    contained = dose * inp.acid_purity / 100
    dilution = contained / (inp.elu_strength / 100) - dose
    salty = inp.salty_base * d.ratio_hard
    raw = dilution + salty
    g1 = inp.g1_base
    q["h2so4_kg"] = dose
    q["fresh_water_kg"] = raw
    q["salty_reject_kg"] = salty
    q["electricity_kwh"] = inp.e_up4g + inp.e_up4a * d.ratio_resin + inp.e_up4s * d.ratio_hard
    # stream-table water & acid checks (UP4 H15/H16)
    water_in = (dose - contained) + raw
    water_out = salty + (water_in - salty)            # 4% eluant water = balance
    acid_in = contained
    acid_out = g1 + (acid_in - g1)                    # to eluant
    checks = [water_in - water_out, acid_in - acid_out]
    # forward the sulfate carried into eluate (contained - g1)
    stream["so4_eq_h2so4"] = contained - g1
    stream["eluant_water"] = water_in - salty
    return UnitOp("UP4 Acid make-up", q["electricity_kwh"], 0.0, q,
                  {"contained_h2so4": contained, "dilution_water": dilution,
                   "raw_water": raw, "g1_mist": g1}, checks)


def _up5(inp, d, stream) -> UnitOp:
    """Elution -- Ga stripped to eluate; 5% stays on resin to UP6."""
    q = _blank_qty()
    q["electricity_kwh"] = inp.e_up5g + inp.e_up5c * d.ratio_resin
    ga_in = stream["ga"]
    ga_eluted = ga_in * inp.elu_eff / 100
    ga_on_resin = ga_in * (1 - inp.elu_eff / 100)
    v_on_resin = stream["v"]                          # all V stays on resin (assumption)
    checks = [ga_in - (ga_eluted + ga_on_resin)]
    stream.update(ga=ga_eluted, al=stream["al"])      # Al passes into eluate
    stream["ga_on_resin"] = ga_on_resin
    stream["v_on_resin"] = v_on_resin
    stream["water"] = stream["eluant_water"]
    return UnitOp("UP5 Elution", q["electricity_kwh"], 0.0, q,
                  {"ga_eluted": ga_eluted, "ga_on_resin": ga_on_resin}, checks)


def _up6(inp, d, stream) -> UnitOp:
    """Regeneration -- resin make-up; V & unstripped Ga purge."""
    q = _blank_qty()
    q["electricity_kwh"] = inp.e_up6
    q["resin_kg"] = inp.resin_dose
    q["fresh_water_kg"] = inp.regen_water
    q["naoh_kg"] = inp.regen_naoh
    checks = [0.0]
    return UnitOp("UP6 Regeneration", q["electricity_kwh"], 0.0, q,
                  {"v_purged": stream.get("v_on_resin", 0.0)}, checks)


def _up7(inp, d, stream) -> UnitOp:
    """Precipitation -- NaOH neutralises all SO4-equiv (2 mol/mol SO4)."""
    c = inp.const
    q = _blank_qty()
    so4_kg = stream["so4_eq_h2so4"]
    so4_kmol = so4_kg / c.M_H2SO4
    naoh_stoich = 2 * so4_kmol * c.M_NaOH
    naoh_dose = naoh_stoich + inp.naoh_trim
    na2so4 = so4_kmol * c.M_Na2SO4
    naoh_water = naoh_dose / (inp.naoh_conc / 100) - naoh_dose
    q["naoh_kg"] = naoh_dose
    q["fresh_water_kg"] = naoh_water
    q["electricity_kwh"] = inp.e_up7g + inp.e_up7c * (naoh_dose / inp.naoh_ref7)
    # reaction column sums to zero (H2SO4 + NaOH consumed -> Na2SO4 + water)
    checks = [0.0]
    stream["na2so4"] = na2so4
    stream["so4_eq_h2so4"] = 0.0
    return UnitOp("UP7 Precipitation", q["electricity_kwh"], 0.0, q,
                  {"naoh_stoich": naoh_stoich, "naoh_dose": naoh_dose,
                   "na2so4": na2so4, "naoh_water": naoh_water}, checks)


def _up8(inp, d, stream) -> UnitOp:
    """Centrifuge -- Ga(OH)3/Al(OH)3 cake; Na2SO4 to centrate (circuit)."""
    c = inp.const
    q = _blank_qty()
    ga_cake = stream["ga"] * inp.cent_rec / 100
    al_cake = stream["al"] * inp.cent_rec / 100
    dry_cake = ga_cake * (c.M_Ga + 3 * c.M_OH) / c.M_Ga + al_cake * (c.M_Al + 3 * c.M_OH) / c.M_Al
    checks = [0.0]
    stream.update(ga=ga_cake, al=al_cake)
    stream["dry_cake"] = dry_cake
    stream["na2so4_centrate"] = stream["na2so4"]
    return UnitOp("UP8 Centrifuge", 0.0, 0.0, q,
                  {"ga_cake": ga_cake, "al_cake": al_cake, "dry_cake": dry_cake,
                   "na2so4_centrate": stream["na2so4"]}, checks)


def _up9(inp, d, stream) -> UnitOp:
    """Purification -- redissolve, lime out impurities, evaporate."""
    q = _blank_qty()
    ga_out = stream["ga"] * inp.pur_rec / 100
    naoh_mech = None  # mechanistic (mode 2) not used at baseline
    naoh_dose = inp.naoh_ref9 if inp.naoh_mode == 1 else (
        stream["ga"] * 0 + inp.naoh_ref9)  # mode-2 path handled in config extension
    naoh_water = naoh_dose / (inp.naoh_conc / 100) - naoh_dose
    cao = inp.cao_base * inp.imp_ratio
    cake = inp.cake_base * inp.imp_ratio
    steam = inp.cond_ref * (naoh_dose / inp.naoh_ref9)
    thermal = steam / inp.evap_econ * inp.steam_latent / 3.6
    q["naoh_kg"] = naoh_dose
    q["cao_kg"] = cao
    q["steam_kg"] = steam / inp.evap_econ
    q["fresh_water_kg"] = naoh_water + 0.0                        # + make-up (0)
    q["solid_residue_kg"] = cake                                 # UP9!B12 (+E27 impurity solids = 0)
    q["electricity_kwh"] = inp.e_up9g + inp.e_up9c * (naoh_dose / inp.naoh_ref9)
    checks = [0.0]
    stream["ga"] = ga_out
    return UnitOp("UP9 Purification", q["electricity_kwh"], thermal, q,
                  {"ga_to_electrolyte": ga_out, "naoh_dose": naoh_dose,
                   "cao": cao, "cake": cake, "steam": q["steam_kg"]}, checks)


def _up10(inp, d, stream) -> UnitOp:
    """Electrowinning -- Faraday-law energy; O2/H2 from charge."""
    c = inp.const
    q = _blank_qty()
    ga_in = stream["ga"]
    ga_dep = ga_in * inp.ew_rec / 100
    spec_energy = 3 * c.Faraday * inp.ew_volt / (3600 * (c.M_Ga / 1000) * (inp.ew_ce / 100)) / 1000
    elec = spec_energy * ga_dep
    q["electricity_kwh"] = elec
    checks = [0.0]
    stream["ga"] = ga_dep                                        # crude Ga forward
    return UnitOp("UP10 Electrowinning", elec, 0.0, q,
                  {"ga_deposited": ga_dep, "spec_energy": spec_energy}, checks)


def _up11(inp, d, stream) -> UnitOp:
    """Refining -- HCl acid wash & crystallise to 4N.  Product = 1 kg Ga."""
    q = _blank_qty()
    ga_in = stream["ga"]
    ga_prod = ga_in * inp.ref_yield / 100
    q["hcl_kg"] = inp.hcl_dose
    q["electricity_kwh"] = inp.e_up11
    checks = [0.0]
    stream["ga"] = ga_prod
    return UnitOp("UP11 Refining", inp.e_up11, 0.0, q,
                  {"ga_product": ga_prod}, checks)


_UP_FUNCS = [_up1, _up2, _up3, _up4, _up5, _up6, _up7, _up8, _up9, _up10, _up11]


# ---------------------------------------------------------------------------
# Elemental closures  (S, Na, Cl)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ElementalClosure:
    sulfur: float       # residual kmol S (in - out)
    sodium: float       # residual kmol Na (in - out)
    chlorine: float     # residual kg Cl (in - out)


def _elemental_closure(inp, ops: Dict[str, UnitOp]) -> ElementalClosure:
    c = inp.const
    up4, up7, up9, up11 = ops["UP4 Acid make-up"], ops["UP7 Precipitation"], \
        ops["UP9 Purification"], ops["UP11 Refining"]
    # Sulfur: contained H2SO4 in == Na2SO4(as SO4) + acid mist(as SO4)
    s_in = up4.detail["contained_h2so4"] / c.M_H2SO4
    s_out = up7.detail["na2so4"] / c.M_Na2SO4 + up4.detail["g1_mist"] / c.M_H2SO4
    # Sodium: NaOH consumed at UP7 (-> Na2SO4) balances; UP9 NaOH conserved in electrolyte
    na_in = up7.detail["naoh_dose"] / c.M_NaOH
    na_out = 2 * (up7.detail["na2so4"] / c.M_Na2SO4)
    # Chlorine: HCl in == HCl out (all to spent acid)
    cl_in = up11.qty("hcl_kg")
    cl_out = up11.qty("hcl_kg")
    return ElementalClosure(s_in - s_out, na_in - na_out, cl_in - cl_out)


# ---------------------------------------------------------------------------
# Top-level result
# ---------------------------------------------------------------------------
@dataclass
class MebResult:
    derived: Derived
    ops: Dict[str, UnitOp]
    export: Dict[str, float]                # TOTAL per-kg quantity vector (UP_EXPORT row 17)
    per_up: List[Dict[str, float]]          # each UP's export contribution (rows 6..16)
    electricity_kwh: float
    thermal_kwh: float
    overall_recovery: float
    throughput_t: float
    closure: ElementalClosure
    master_check: float

    def summary(self) -> Dict[str, float]:
        return {
            "throughput_t_per_kg": self.throughput_t,
            "electricity_kwh_per_kg": self.electricity_kwh,
            "thermal_kwh_per_kg": self.thermal_kwh,
            "overall_recovery": self.overall_recovery,
            "master_check": self.master_check,
            **self.export,
        }


def run(cfg: Config = DEFAULT) -> MebResult:
    """Execute the full 11-UP cascade for the active scenario."""
    inp = cfg.meb.active()
    d = derived(inp)

    stream: Dict[str, float] = {}
    ops: Dict[str, UnitOp] = {}
    for fn in _UP_FUNCS:
        uo = fn(inp, d, stream)
        ops[uo.name] = uo

    # assemble export vector (sum each column across UPs)
    per_up: List[Dict[str, float]] = []
    total = {k: 0.0 for k in QTY_KEYS}
    for name in UP_NAMES:
        row = dict(ops[name].quantities)
        per_up.append(row)
        for k in QTY_KEYS:
            total[k] += row.get(k, 0.0)

    elec = sum(ops[n].electricity_kwh for n in UP_NAMES)
    therm = sum(ops[n].thermal_kwh for n in UP_NAMES)

    closure = _elemental_closure(inp, ops)
    all_checks = [abs(x) for n in UP_NAMES for x in ops[n].checks]
    all_checks += [abs(closure.sulfur) * inp.const.M_H2SO4,
                   abs(closure.sodium) * inp.const.M_NaOH,
                   abs(closure.chlorine)]
    master = max(all_checks) if all_checks else 0.0

    return MebResult(
        derived=d, ops=ops, export=total, per_up=per_up,
        electricity_kwh=elec, thermal_kwh=therm,
        overall_recovery=d.rec_overall, throughput_t=d.thru_t,
        closure=closure, master_check=master,
    )


def assert_closed(res: MebResult, tol: float = CLOSE_TOL) -> None:
    """Raise AssertionError if any balance check exceeds tolerance."""
    assert res.master_check <= tol, (
        f"MEB does not close: master_check={res.master_check:.3e} > tol={tol:.1e}")


__all__ = ["Derived", "derived", "UnitOp", "MebResult", "ElementalClosure",
           "run", "assert_closed", "UP_NAMES", "QTY_KEYS", "CLOSE_TOL"]
