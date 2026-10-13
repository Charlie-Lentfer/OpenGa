"""
openga_v1.equipment
===================

Sixteen major items, each sized from the MEB and costed with a published
purchased-equipment correlation of the form

    Ce = a + b * S ** n          (Towler & Sinnott, Chemical Engineering Design,
                                  2nd ed., Table 7.2. Basis: US Gulf Coast,
                                  January 2010, CEPCI = 532.9, 2010 US$.)

Every item carries an in-range flag against the correlation's published S
minimum and maximum. A correlation used outside its range is not an error the
model can catch for you, but it is one you should see.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from .meb import MEBResult

# id: (description, size parameter, S min, S max, a, b, n)
CORRELATIONS: dict[str, tuple[str, str, float, float, float, float, float]] = {
    "E01": ("Centrifugal pump, single stage", "flow, L/s", 0.2, 126, 8_000, 240, 0.9),
    "E02": ("Explosion-proof electric motor", "power, kW", 1, 2_500, -1_100, 2_100, 0.6),
    "E03": ("Vertical pressure vessel, 304 SS", "shell mass, kg", 120, 250_000, 17_400, 79, 0.85),
    "E04": ("Cone-roof storage tank", "capacity, m3", 10, 4_000, 5_800, 1_600, 0.7),
    "E05": ("Jacketed agitated reactor, 304 SS", "volume, m3", 0.5, 100, 61_500, 32_500, 0.8),
    "E06": ("Filter, plate and frame", "capacity, m3", 0.4, 1.4, 128_000, 89_000, 0.5),
    "E07": ("Filter, vacuum drum", "area, m2", 10, 180, -73_000, 93_000, 0.3),
    "E08": ("Centrifuge, high-speed disk", "diameter, m", 0.26, 0.49, 57_000, 480_000, 0.7),
    "E09": ("Evaporator, vertical tube", "area, m2", 11, 640, 330, 36_000, 0.55),
    "E10": ("Heat exchanger, plate and frame", "area, m2", 1, 500, 1_600, 210, 0.95),
}


@dataclass
class EquipItem:
    id: str
    name: str
    unit_op: str
    corr: str
    basis: str
    n_duty: float = 0.0
    s_each: float = 0.0
    s_unit: str = ""
    s_min: float = 0.0
    s_max: float = 0.0
    in_range: str = ""
    ce_each_usd2010: float = 0.0
    ce_total_usd2010: float = 0.0
    mat_factor: float = 1.0
    hand_factor: float = 1.0
    installed_usd2010: float = 0.0
    note: str = ""


@dataclass
class EquipResult:
    items: list[EquipItem] = field(default_factory=list)
    pce_usd2010: float = 0.0            # itemised purchased equipment
    misc_allowance: float = 0.0
    spares_allowance: float = 0.0
    pce_total_usd2010: float = 0.0
    installed_usd2010: float = 0.0
    direct_aud: float = 0.0             # resin charge + rectifier, already AUD
    resin_charge_aud: float = 0.0
    rectifier_aud: float = 0.0
    out_of_range: int = 0
    installed_by_up: dict[str, float] = field(default_factory=dict)


def _ce(corr: str, s: float) -> float:
    _d, _u, _lo, _hi, a, b, n = CORRELATIONS[corr]
    if s <= 0:
        return 0.0
    return a + b * s ** n


def _units(total_s: float, s_max: float) -> float:
    if total_s <= 0:
        return 0.0
    return max(1.0, math.ceil(total_s / s_max))


def run(p: dict, m: MEBResult) -> EquipResult:
    r = EquipResult()
    liq_ls = m.liquor_m3_h / 3.6
    filt_area = m.liquor_m3_h / p["FiltFlux"] if p["FiltFlux"] else 0.0
    ix_shell = (math.pi * m.col_dia_m * (p["IXBed"] / p["VesFill"])
                * p["VesThk"] / 1000.0 * p["SteelDens"] * p["HeadAllow"])
    ew_cell_vol = m.elyte_vol_L * p["CapProd"] / p["OpHours"] / 1000.0 * p["EWRes"] / p["VesFill"]
    ew_side = (4 * ew_cell_vol / math.pi) ** (1 / 3) if ew_cell_vol > 0 else 0.0
    ew_shell = (math.pi * ew_side * ew_side * p["VesThk"] / 1000.0
                * p["SteelDens"] * p["HeadAllow"])
    sec_ls = (m.wash_m3_yr + m.elu_m3_yr + m.regen_m3_yr) / p["OpHours"] / 3.6

    MAT, HP, HV, HX, HM = p["MatFac"], p["HandPump"], p["HandVes"], p["HandHX"], p["HandMisc"]

    # (id, name, unit op, correlation, sizing note, total S, fixed N or None,
    #  material factor, hand factor)
    spec = [
        ("EQ01", "Liquor feed pumps", "UP2", "E01",
         "Liquor volumetric flow", liq_ls, None, 1.0, HP),
        ("EQ02", "Liquor pump motors", "UP2", "E02",
         "Hydraulic power / efficiency", m.kw_liquor, None, 1.0, HP),
        ("EQ03", "Liquor polishing filters", "UP1", "E07",
         "Liquor flow / filtration flux", filt_area, None, 1.0, HM),
        ("EQ04", "Ion exchange columns", "UP2", "E03",
         "Bed diameter and depth from superficial velocity",
         ix_shell * p["IXColTot"], p["IXColTot"], MAT, HV),
        ("EQ05", "Precipitation reactors", "UP7", "E05",
         "Slurry flow x residence time / fill fraction", m.react_vol_m3 * 2, 2, MAT, HV),
        ("EQ06", "Centrifuges", "UP8", "E08",
         "Slurry flow / hydraulic capacity per machine",
         p["CentDia"] * m.cent_units, m.cent_units, MAT, HM),
        ("EQ07", "Purification reactor", "UP9", "E05",
         "Purification duty, small relative to precipitation", m.react_vol_m3 / 2, 1, MAT, HV),
        ("EQ08", "Purification filter", "UP9", "E06",
         "Purification cake filtration", 0.4, 1, 1.0, HM),
        ("EQ09", "Evaporator", "UP9", "E09",
         "Evaporation duty / (U x delta T)", m.evap_area_m2, None, 1.0, HX),
        ("EQ10", "Electrowinning cells", "UP10", "E03",
         "Electrolyte circulation x residence time / fill fraction", ew_shell, 1, MAT, HV),
        ("EQ11", "Refining vessel", "UP11", "E05",
         "Acid wash and casting, small batch duty", 1.0, 1, MAT, HV),
        ("EQ12", "H2SO4 storage tank", "UP4", "E04",
         "Delivered acid consumption x storage days", m.tank_acid_m3, None, 1.0, HV),
        ("EQ13", "NaOH storage tank", "UP7", "E04",
         "Caustic solution consumption x storage days", m.tank_naoh_m3, None, 1.0, HV),
        ("EQ14", "Process water tank", "UP4", "E04",
         "Raw water intake x storage days", m.tank_water_m3, None, 1.0, HV),
        ("EQ15", "Eluant make-up tank", "UP4", "E04",
         "Eluant throughput x storage days", m.tank_elu_m3, None, MAT, HV),
        # Four pumps SHARE the combined secondary flow, so the size each one
        # sees is the total divided by four, not the total.
        ("EQ16", "Wash, eluant and transfer pumps", "UP3", "E01",
         "Combined secondary flow, split across four pumps", sec_ls, 4, 1.0, HP),
    ]

    for eid, name, up, corr, basis, total_s, fixed_n, mat, hand in spec:
        desc, sunit, smin, smax, *_ = CORRELATIONS[corr]
        n = float(fixed_n) if fixed_n is not None else _units(total_s, smax)
        s_each = (total_s / n) if n else 0.0
        it = EquipItem(id=eid, name=name, unit_op=up, corr=corr, basis=basis,
                       n_duty=n, s_each=s_each, s_unit=sunit, s_min=smin, s_max=smax,
                       mat_factor=mat, hand_factor=hand)
        if n == 0:
            it.in_range = "not required"
        elif smin <= s_each <= smax:
            it.in_range = "in range"
        else:
            it.in_range = "OUT OF RANGE"
            r.out_of_range += 1
        it.ce_each_usd2010 = _ce(corr, s_each) if n else 0.0
        it.ce_total_usd2010 = it.ce_each_usd2010 * n
        it.installed_usd2010 = it.ce_total_usd2010 * mat * hand
        r.items.append(it)

    r.pce_usd2010 = sum(i.ce_total_usd2010 for i in r.items)
    r.misc_allowance = r.pce_usd2010 * p["MiscEquip"] / 100.0
    pumps = r.items[0].ce_total_usd2010 + r.items[15].ce_total_usd2010
    r.spares_allowance = pumps * p["SparePct"] / 100.0
    r.pce_total_usd2010 = r.pce_usd2010 + r.misc_allowance + r.spares_allowance

    inst_items = sum(i.installed_usd2010 for i in r.items)
    inst_misc = inst_items * p["MiscEquip"] / 100.0
    inst_pumps = r.items[0].installed_usd2010 + r.items[15].installed_usd2010
    inst_spares = inst_pumps * p["SparePct"] / 100.0
    r.installed_usd2010 = inst_items + inst_misc + inst_spares

    r.resin_charge_aud = m.resin_total_kg * p["P_RESIN"] * p["RESINCAPEX"]
    r.rectifier_aud = m.ew_kw * p["EWRectCost"]
    r.direct_aud = r.resin_charge_aud + r.rectifier_aud

    by_up: dict[str, float] = {}
    for i in r.items:
        by_up[i.unit_op] = by_up.get(i.unit_op, 0.0) + i.installed_usd2010
    r.installed_by_up = by_up
    return r
