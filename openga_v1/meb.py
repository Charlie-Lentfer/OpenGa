"""
openga_v1.meb
=============

Mass and energy balance on a basis of one kilogram of 4N gallium.

Eleven unit operations, one recovery each. Reagent doses come from resin
chemistry and stoichiometry. Energy comes from duty. Nothing is scaled from a
reference plant — except in ``energy_mode="legacy_wp3"``, which reinstates the
WP3 behaviour of scaling Luo et al.'s per-unit allocation by throughput, resin
and hardness ratios, and is offered only so the older figures can be
reproduced.

The two modes disagree by roughly a factor of seven: at the shipped 70 mg/L
assay, 19.83 kWh/kg mechanistic against 174.9 kWh/kg legacy. That is not a bug
in either. Luo's allocation cannot be reconciled with a pumping calculation at
any plausible head — you would need about 460 m — so the mechanistic route is
the defensible one and is the default. The legacy route is kept because
earlier submitted work quotes it.

One caveat on the legacy route, stated plainly. It reinstates WP3's ENERGY
allocation on top of the v3.3 physical basis. It does NOT restore WP3's
six-stage recovery cascade, so it will not reproduce the old 143.558 kWh/kg
exactly even at the old 103 mg/L assay — it returns about 140.3. If you need
the original figure to the decimal, quote it from the WP3 workbook, not from
here.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class MEBResult:
    # cascade
    recoveries: dict[str, float] = field(default_factory=dict)
    ga_out: dict[str, float] = field(default_factory=dict)
    recovery_overall: float = 0.0
    feed_ga_kg: float = 0.0

    # throughput
    liquor_kg_per_kg: float = 0.0
    liquor_t_per_kg: float = 0.0
    liquor_t_yr: float = 0.0
    liquor_m3_h: float = 0.0

    # ion exchange
    ga_load_kg_h: float = 0.0
    v_load_kg_h: float = 0.0
    al_load_kg_h: float = 0.0
    bed_area_m2: float = 0.0
    col_dia_m: float = 0.0
    bed_vol_m3: float = 0.0
    resin_col_kg: float = 0.0
    resin_load_kg: float = 0.0
    resin_total_kg: float = 0.0
    cycle_h: float = 0.0
    bv_per_h: float = 0.0
    wash_m3_yr: float = 0.0
    elu_m3_yr: float = 0.0
    regen_m3_yr: float = 0.0
    resin_makeup_kg_yr: float = 0.0

    # reagents, kg per kg Ga
    h2so4_contained: float = 0.0
    h2so4_delivered: float = 0.0
    naoh_up7: float = 0.0
    naoh_up9: float = 0.0
    naoh_total: float = 0.0
    na2so4: float = 0.0
    cao: float = 0.0
    hcl: float = 0.0
    resin_makeup: float = 0.0

    # water
    w_wash: float = 0.0
    w_elu: float = 0.0
    w_regen: float = 0.0
    w_makeup: float = 0.0
    w_net_m3_yr: float = 0.0
    w_raw_m3_yr: float = 0.0
    w_rej_m3_yr: float = 0.0
    w_wash_kg: float = 0.0
    w_elu_kg: float = 0.0
    w_regen_kg: float = 0.0
    w_makeup_kg: float = 0.0
    w_net_kg: float = 0.0
    w_raw_kg: float = 0.0
    w_rej_kg: float = 0.0

    # energy
    kw_liquor: float = 0.0
    kw_secondary: float = 0.0
    kw_ew: float = 0.0
    kw_misc: float = 0.0
    kw_total: float = 0.0
    elec_kwh_kg: float = 0.0
    steam_kg_kg: float = 0.0
    evap_kg_h: float = 0.0
    evap_area_m2: float = 0.0
    ew_kwh_kg_deposited: float = 0.0
    ew_amps: float = 0.0
    ew_kw: float = 0.0
    energy_mode: str = "mechanistic"
    energy_by_up: dict[str, float] = field(default_factory=dict)

    # downstream solids
    ga_cake: float = 0.0
    ga_elyte: float = 0.0
    ga_crude: float = 0.0
    al_cake: float = 0.0
    dry_cake: float = 0.0
    precip_grade: float = 0.0
    cake_h2o: float = 0.0
    solid_residue: float = 0.0
    elyte_vol_L: float = 0.0
    slurry_m3_h: float = 0.0
    react_vol_m3: float = 0.0
    cent_units: int = 0

    # storage
    tank_acid_m3: float = 0.0
    tank_naoh_m3: float = 0.0
    tank_water_m3: float = 0.0
    tank_elu_m3: float = 0.0

    notes: list[str] = field(default_factory=list)


UP_KEYS = ["UP1", "UP2", "UP3", "UP4", "UP5", "UP6", "UP7", "UP8", "UP9", "UP10", "UP11"]


def run(p: dict, energy_mode: str = "mechanistic") -> MEBResult:
    r = MEBResult(energy_mode=energy_mode)

    # ---------------------------------------------------------------- cascade
    # UP1 loss is DERIVED from the suspended-solids load and cake moisture:
    # gallium leaves only in the liquor the filter cake carries out with it.
    up1 = 1.0 - p["SSLoad"] * p["FiltCakeMoist"] / (100.0 - p["FiltCakeMoist"]) / 1000.0
    rec = {
        "UP1": up1,
        "UP2": p["IXRec"] / 100.0,
        "UP3": p["WashRec"] / 100.0,
        "UP4": 1.0,
        "UP5": p["EluEff"] / 100.0,
        "UP6": 1.0,
        "UP7": p["PrecRec"] / 100.0,
        "UP8": p["CentRec"] / 100.0,
        "UP9": p["PurRec"] / 100.0,
        "UP10": p["EWRec"] / 100.0,
        "UP11": p["RefYield"] / 100.0,
    }
    overall = 1.0
    for k in UP_KEYS:
        overall *= rec[k]
    r.recoveries = rec
    r.recovery_overall = overall
    r.feed_ga_kg = 1.0 / overall

    ga = r.feed_ga_kg
    for k in UP_KEYS:
        ga *= rec[k]
        r.ga_out[k] = ga

    # ------------------------------------------------------------- throughput
    mass_frac = p["GaFeed"] / (1e6 * p["LiqDensity"])          # kg Ga / kg liquor
    r.liquor_kg_per_kg = r.feed_ga_kg / mass_frac
    r.liquor_t_per_kg = r.liquor_kg_per_kg / 1000.0
    r.liquor_t_yr = r.liquor_t_per_kg * p["CapProd"]
    r.liquor_m3_h = r.liquor_t_yr / p["OpHours"] / p["LiqDensity"]

    # ---------------------------------------------------------- ion exchange
    Q = r.liquor_m3_h
    r.ga_load_kg_h = Q * p["GaFeed"] * p["IXRec"] / 100.0 / 1000.0
    r.v_load_kg_h = Q * p["VFeed"] * p["CoAdsV"] / 100.0 / 1000.0
    r.al_load_kg_h = Q * p["AlFeed"] * p["CoAdsAl"] / 100.0     # AlFeed in g/L -> kg/h
    total_load = r.ga_load_kg_h + r.v_load_kg_h

    r.bed_area_m2 = Q / p["IXVel"]
    ncol_load = max(1.0, p["IXColLoad"])
    r.col_dia_m = (4.0 * r.bed_area_m2 / ncol_load / 3.141592653589793) ** 0.5
    r.bed_vol_m3 = r.bed_area_m2 / ncol_load * p["IXBed"]
    r.resin_col_kg = r.bed_vol_m3 * p["ResinBulk"] * 1000.0
    r.resin_load_kg = r.resin_col_kg * ncol_load
    r.resin_total_kg = r.resin_col_kg * p["IXColTot"]
    r.cycle_h = (r.resin_load_kg * p["ResinCap"] / 1000.0 / total_load) if total_load else 0.0

    # The key result: bed volumes turned over per hour is independent of column
    # diameter and superficial velocity. Wash, eluant and regeneration volumes
    # all scale from it, so they do not depend on how the bed is arranged.
    r.bv_per_h = total_load / (p["ResinBulk"] * 1000.0 * p["ResinCap"] / 1000.0)

    H = p["OpHours"]
    r.wash_m3_yr = p["WashBV"] * r.bv_per_h * H
    r.elu_m3_yr = p["EluBV"] * r.bv_per_h * H
    r.regen_m3_yr = p["RegenBV"] * r.bv_per_h * H
    r.resin_makeup_kg_yr = r.resin_total_kg / p["ResinLife"]

    # --------------------------------------------------------------- reagents
    C = p["CapProd"]
    r.h2so4_contained = r.elu_m3_yr * p["EluDens"] * 1000.0 * p["EluStrength"] / 100.0 / C
    r.h2so4_delivered = r.h2so4_contained / (p["AcidPurity"] / 100.0)
    # Stoichiometric: 2 mol NaOH per mol sulfate. Free acid and Ga2(SO4)3 need
    # the same two equivalents, so one term covers both.
    r.naoh_up7 = 2.0 * (r.h2so4_contained / p["MH2SO4"]) * p["MNaOH"] + p["NaOHTrim"]
    r.naoh_up9 = p["NaOH_UP9"]
    r.naoh_total = r.naoh_up7 + r.naoh_up9
    r.na2so4 = (r.h2so4_contained / p["MH2SO4"]) * p["MNa2SO4"]
    r.cao = p["CaODose"] * p["ImpRatio"]
    r.hcl = p["HClDose"]
    r.resin_makeup = r.resin_makeup_kg_yr / C

    # ------------------------------------------------------------------ water
    r.w_wash = r.wash_m3_yr
    r.w_elu = (r.elu_m3_yr * p["EluDens"] * 1000.0 - r.h2so4_delivered * C) / 1000.0
    r.w_regen = r.regen_m3_yr

    # -------------------------------------------------- downstream solids (pt 1)
    r.ga_cake = r.ga_out["UP8"]
    r.ga_elyte = r.ga_out["UP9"]
    r.ga_crude = r.ga_out["UP10"]
    r.al_cake = r.al_load_kg_h * H / C * p["CentRec"] / 100.0
    r.dry_cake = (r.ga_cake * (p["MGa"] + 3 * p["MOH"]) / p["MGa"]
                  + r.al_cake * (p["MAl"] + 3 * p["MOH"]) / p["MAl"])
    r.precip_grade = r.ga_cake / r.dry_cake if r.dry_cake else 0.0
    r.cake_h2o = r.dry_cake / (1.0 - p["CakeMoist"] / 100.0) - r.dry_cake

    r.elyte_vol_L = r.ga_elyte / p["ElecGa"] * 1000.0
    elyte_mass = r.elyte_vol_L * p["ElecDens"]
    elyte_naoh = r.elyte_vol_L * p["ElecNaOH"] / 1000.0
    elyte_water_req = elyte_mass - r.ga_elyte - elyte_naoh
    up9_water_in = r.cake_h2o + r.naoh_up9 / (p["NaOHConc"] / 100.0) - r.naoh_up9

    r.w_makeup = max(0.0, elyte_water_req - up9_water_in) * C / 1000.0
    r.w_net_m3_yr = r.w_wash + r.w_elu + r.w_regen + r.w_makeup
    r.w_raw_m3_yr = r.w_net_m3_yr / (1.0 - p["SoftReject"])
    r.w_rej_m3_yr = r.w_raw_m3_yr - r.w_net_m3_yr
    for a, b in [("w_wash", "w_wash_kg"), ("w_elu", "w_elu_kg"), ("w_regen", "w_regen_kg"),
                 ("w_makeup", "w_makeup_kg")]:
        setattr(r, b, getattr(r, a) * 1000.0 / C)
    r.w_net_kg = r.w_net_m3_yr * 1000.0 / C
    r.w_raw_kg = r.w_raw_m3_yr * 1000.0 / C
    r.w_rej_kg = r.w_rej_m3_yr * 1000.0 / C

    # Evaporation only happens when the incoming water exceeds what the
    # electrolyte can hold. Under the mechanistic caustic dose it does not.
    r.evap_kg_h = max(0.0, up9_water_in - elyte_water_req) * C / H
    r.steam_kg_kg = r.evap_kg_h * H / p["EvapEcon"] / C
    evap_duty_kw = r.evap_kg_h * p["SteamLatent"] / 3.6
    r.evap_area_m2 = (0.0 if r.evap_kg_h == 0 else
                      r.evap_kg_h * p["SteamLatent"] * 1e6 / 3600.0 / (p["EvapU"] * p["EvapDT"]))

    # ----------------------------------------------------------------- energy
    # Electrowinning from Faraday's law: z F V / (3600 M CE)
    r.ew_kwh_kg_deposited = (3 * p["FarC"] * p["EWVolt"]
                             / (3600.0 * (p["MGa"] / 1000.0) * (p["EWCE"] / 100.0)) / 1000.0)
    r.ew_amps = 3 * (r.ga_crude * C / H / p["MGa"] * 1000.0) * p["FarC"] / (p["EWCE"] / 100.0) / 3600.0
    r.ew_kw = r.ew_amps * p["EWVolt"] / 1000.0

    if energy_mode == "legacy_wp3":
        _legacy_energy(p, r)
    else:
        _mechanistic_energy(p, r)

    # --------------------------------------------------- downstream (pt 2)
    r.solid_residue = (r.al_cake * (p["MAl"] + 3 * p["MOH"]) / p["MAl"]
                       + r.cao + r.ga_cake - r.ga_elyte) + r.resin_makeup
    eluate_m3_h = r.elu_m3_yr / H
    naoh_m3_h = r.naoh_up7 * C / (p["NaOHConc"] / 100.0) / p["NaOHDens"] / 1000.0 / H
    r.slurry_m3_h = eluate_m3_h + naoh_m3_h
    r.react_vol_m3 = r.slurry_m3_h * p["ReactRes"] / p["VesFill"]
    r.cent_units = int(-(-r.slurry_m3_h // p["CentCap"])) if p["CentCap"] else 0

    # ---------------------------------------------------------------- storage
    d = p["TankDays"] / 365.0 / p["VesFill"]
    r.tank_acid_m3 = r.h2so4_delivered * C / p["AcidDens"] / 1000.0 * d
    r.tank_naoh_m3 = r.naoh_total * C / (p["NaOHConc"] / 100.0) / p["NaOHDens"] / 1000.0 * d
    r.tank_water_m3 = r.w_raw_m3_yr * d
    r.tank_elu_m3 = r.elu_m3_yr * d

    # ------------------------------------------------------------------ notes
    if r.cycle_h < 8:
        r.notes.append(f"Loading cycle {r.cycle_h:.1f} h — below about 8 h the bed is too "
                       "small to be practical.")
    if r.cycle_h > 100:
        r.notes.append(f"Loading cycle {r.cycle_h:.1f} h — above about 100 h the bed is "
                       "over-sized for its duty.")
    if r.precip_grade < 0.05:
        r.notes.append(f"Precipitate grade {r.precip_grade * 100:.1f}% Ga — aluminium "
                       "carry-over is dominating the cake.")
    return r


def _mechanistic_energy(p: dict, r: MEBResult) -> None:
    """Pumping from P = rho.g.Q.H/eta, electrowinning from Faraday, plus an
    ancillary allowance. This replaces the reference-plant allocation."""
    eta = p["PumpEff"] / 100.0
    r.kw_liquor = (p["LiqDensity"] * 1000.0 * p["GRAV"] * (r.liquor_m3_h / 3600.0)
                   * p["PumpHead"] / eta / 1000.0)
    sec_m3_h = (r.wash_m3_yr + r.elu_m3_yr + r.regen_m3_yr) / p["OpHours"]
    r.kw_secondary = (1000.0 * p["GRAV"] * (sec_m3_h / 3600.0) * p["WashHead"] / eta / 1000.0)
    r.kw_ew = r.ew_kwh_kg_deposited * r.ga_crude * p["CapProd"] / p["OpHours"]
    sub = r.kw_liquor + r.kw_secondary + r.kw_ew
    r.kw_misc = sub * p["MiscElec"] / 100.0
    r.kw_total = sub + r.kw_misc
    r.elec_kwh_kg = r.kw_total * p["OpHours"] / p["CapProd"]


def _legacy_energy(p: dict, r: MEBResult) -> None:
    """WP3 behaviour: Luo et al.'s per-unit-operation kWh/kg allocation, scaled
    by throughput, resin-inventory and water-hardness ratios.

    Carried so the earlier figures can be reproduced. It is an allocation, not
    a calculation: none of these numbers can be checked against a duty.
    """
    L = _LEGACY
    # Ratios exactly as WP3 defines them: this plant against the same cascade
    # evaluated at Luo's liquor chemistry, so the feed-gallium requirement
    # cancels and only the concentrations move.
    thru_kg = r.liquor_kg_per_kg
    thru_L = thru_kg / p["LiqDensity"]
    thru_kg_base = r.feed_ga_kg / (L["ga_conc_luo"] / (1e6 * p["LiqDensity"]))
    thru_L_base = thru_kg_base / p["LiqDensity"]
    ratio_t = thru_kg / thru_kg_base

    ga_ads = r.feed_ga_kg * p["IXRec"] / 100.0
    v_ads = (p["VFeed"] / 1e6) * thru_L * (p["CoAdsV"] / 100.0)
    v_ads_base = (L["v_conc_luo"] / 1e6) * thru_L_base * (p["CoAdsV"] / 100.0)
    cap = p["ResinCap"] / 1000.0
    resin_inv = (ga_ads + v_ads) / cap
    resin_inv_base = (ga_ads + v_ads_base) / cap
    ratio_resin = resin_inv / resin_inv_base if resin_inv_base else 1.0

    ratio_hard = p.get("SiteHardness", L["hardness_site"]) / L["hardness_ref"]
    naoh_ratio = r.naoh_up7 / L["naoh7_luo"] if L["naoh7_luo"] else 1.0

    e = {
        "UP1": L["e_up1"] * ratio_t,
        "UP2": L["e_up2"] * ratio_t,
        "UP3": L["e_up3"] * ratio_resin,
        "UP4": L["e_up4_general"] + L["e_up4_acid"] * ratio_resin + L["e_up4_soften"] * ratio_hard,
        "UP5": L["e_up5_general"] + L["e_up5_cool"] * ratio_resin,
        "UP6": L["e_up6"],
        "UP7": L["e_up7_general"] + L["e_up7_cool"] * naoh_ratio,
        "UP8": L["e_up8"],
        "UP9": L["e_up9_general"] + L["e_up9_cool"] * naoh_ratio,
        "UP10": r.ew_kwh_kg_deposited * r.ga_crude,   # still Faraday, as WP3 did
        "UP11": L["e_up11"],
    }
    r.energy_by_up = e
    r.elec_kwh_kg = sum(e.values())
    r.kw_total = r.elec_kwh_kg * p["CapProd"] / p["OpHours"]
    r.kw_ew = e["UP10"] * p["CapProd"] / p["OpHours"]
    r.kw_liquor = (e["UP1"] + e["UP2"]) * p["CapProd"] / p["OpHours"]
    r.kw_secondary = (e["UP3"] + e["UP5"]) * p["CapProd"] / p["OpHours"]
    r.kw_misc = r.kw_total - r.kw_liquor - r.kw_secondary - r.kw_ew
    r.notes.append(
        "Legacy WP3 energy mode: electricity is Luo et al.'s allocation scaled by "
        "throughput, resin and hardness ratios, not computed from duty. It cannot be "
        "reconciled with a pumping calculation at any plausible head.")


# WP3 legacy energy constants (Luo et al. baseline column)
_LEGACY = {
    "e_up1": 17.23, "e_up2": 11.39, "e_up3": 3.27,
    "e_up4_general": 9.0, "e_up4_acid": 0.72, "e_up4_soften": 1.35,
    "e_up5_general": 4.55, "e_up5_cool": 26.1,
    "e_up6": 1.98,
    "e_up7_general": 4.75, "e_up7_cool": 1.81,
    "e_up8": 0.0,
    "e_up9_general": 13.27, "e_up9_cool": 1.81,
    "e_up11": 0.29,
    "ga_conc_luo": 230.0, "v_conc_luo": 149.6,
    "hardness_ref": 150.0, "hardness_site": 80.0,
    "naoh7_luo": 44.84,
}
