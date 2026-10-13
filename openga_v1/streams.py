"""Build the flowsheet register from V1's resolved parameters and MEB result.

The original stream IDs are retained, but numeric snapshot values are never
loaded. This is a reporting extension: it does not replace the V1 MEB or feed
new quantities into equipment, costs or carbon. Assumptions follow the supplied
stream register (all Al eluted, V retained for regeneration; no acid mist).

Totals conserve mass using a lumped liquid/water balance, as in the supplied
adapter. This is not a full chemical speciation or hydrogen/oxygen balance.
"""
from __future__ import annotations

from functools import lru_cache
import json
import math
from pathlib import Path

from .meb import MEBResult


@lru_cache(maxsize=1)
def _metadata():
    data = json.loads(Path(__file__).with_name("stream_metadata.json").read_text())
    return {s["id"]: s for s in data["streams"]}


# Explicit treatment interface: S30P terminates at neutralisation, rather than
# being claimed as treated effluent. Never add S30 to its two child streams.
INPUT_IDS = ("S1", "S9", "S10", "S17", "S20", "S24", "S25", "S32")
OUTPUT_IDS = ("S2", "S4", "S7", "S11", "S12", "S18", "S19", "S22", "S26",
              "S27", "S29", "S30P", "S33", "S34")
UNIT_STREAMS = {
    "UP1": (("S1",), ("S2", "S3")),
    "UP2": (("S3",), ("S4", "S5")),
    "UP3": (("S5", "S6"), ("S7", "S8")),
    "UP4": (("S9", "S10"), ("S6", "S11", "S12", "S13", "S16", "S25b")),
    "UP5": (("S8", "S13"), ("S14", "S15")),
    "UP6": (("S15", "S16", "S17"), ("S18", "S19")),
    "UP7": (("S14", "S20"), ("S21",)),
    "UP8": (("S21",), ("S22", "S23")),
    "UP9": (("S23", "S24", "S25", "S25b", "S30R"), ("S26", "S27", "S28")),
    "UP10": (("S28",), ("S29", "S30", "S31")),
    "UP11": (("S31", "S32"), ("S33", "S34")),
    "Electrolyte split": (("S30",), ("S30R", "S30P")),
    "Reported boundary": (INPUT_IDS, OUTPUT_IDS),
}


def build_streams(p: dict, m: MEBResult) -> dict:
    """Return current amounts on the V1 basis of kg per kg 4N gallium product.

    V1 has no electrolyte recycle calculation. S30R is therefore zero and S30P
    is the full spent electrolyte. Do not infer a recycle benefit from this
    reporting extension. HCl retains V1's 100% equivalent cost/mass basis.
    """
    if p.get("EWRecycle", 0):
        raise ValueError("The V1 MEB has no electrolyte recycle model. EWRecycle must be zero.")
    s: dict[str, dict[str, float]] = {}
    ga_ratio = (p["MGa"] + 3 * p["MOH"]) / p["MGa"]
    al_ratio = (p["MAl"] + 3 * p["MOH"]) / p["MAl"]

    def put(sid, **values):
        s[sid] = {k: float(v) for k, v in values.items()}

    def total(sid):
        return math.fsum(s[sid].values())

    def sub(a, b):
        return {k: s[a].get(k, 0) - s[b].get(k, 0) for k in sorted(s[a].keys() | s[b].keys())}

    # Host liquor and solids removal. The Ga loss follows the actual MEB cascade.
    thru, rho = m.liquor_kg_per_kg, p["LiqDensity"]
    al = thru * p["AlFeed"] / (1000 * rho)
    v = thru * p["VFeed"] / (1e6 * rho)
    ss = thru * p["SSLoad"] / 1000
    entrained = ss * p["FiltCakeMoist"] / (100 - p["FiltCakeMoist"])
    ga_frac = p["GaFeed"] / (1e6 * rho)
    al_frac, v_frac = p["AlFeed"] / (1000 * rho), p["VFeed"] / (1e6 * rho)
    put("S1", Ga=m.feed_ga_kg, Al=al, V=v, SS=ss,
        LiqBal=thru - m.feed_ga_kg - al - v - ss)
    put("S2", SS=ss, Ga=m.feed_ga_kg - m.ga_out["UP1"], Al=entrained * al_frac,
        V=entrained * v_frac, LiqBal=entrained * (1 - ga_frac - al_frac - v_frac))
    s["S3"] = sub("S1", "S2")

    # V1's Al/V uptake quantities are used directly to match its downstream cake.
    uptake_scale = p["OpHours"] / p["CapProd"]
    al_ads, v_ads = m.al_load_kg_h * uptake_scale, m.v_load_kg_h * uptake_scale
    put("S5", Ga=m.ga_out["UP2"], Al=al_ads, V=v_ads)
    s["S4"] = sub("S3", "S5")
    put("S6", Water=m.w_wash_kg)
    put("S7", Water=m.w_wash_kg, Ga=m.ga_out["UP2"] - m.ga_out["UP3"])
    put("S8", Ga=m.ga_out["UP3"], Al=al_ads, V=v_ads)

    # Water treatment and acid preparation; V1 does not calculate an acid mist.
    put("S9", H2SO4=m.h2so4_contained, Water=m.h2so4_delivered - m.h2so4_contained)
    put("S10", Water=m.w_raw_kg)
    put("S11", Water=m.w_rej_kg)
    put("S12", H2SO4=0)
    put("S13", H2SO4=m.h2so4_contained,
        Water=m.w_elu_kg + s["S9"]["Water"])
    put("S14", Ga=m.ga_out["UP5"], Al=al_ads, V=0,
        H2SO4=s["S13"]["H2SO4"], Water=s["S13"]["Water"])
    put("S15", Ga=m.ga_out["UP3"] - m.ga_out["UP5"], Al=0, V=v_ads)
    put("S16", Water=m.w_regen_kg)
    put("S17", Resin=m.resin_makeup)
    put("S18", Water=m.w_regen_kg, Ga=s["S15"]["Ga"], V=v_ads)
    put("S19", Resin=m.resin_makeup)

    put("S20", NaOH=m.naoh_up7, Water=m.naoh_up7 * (100 / p["NaOHConc"] - 1))
    ga_hydroxide = m.ga_out["UP7"] * ga_ratio
    # Dissolved Ga stays in centrate when precipitation recovery is below 100%.
    ga_dissolved = m.ga_out["UP5"] - m.ga_out["UP7"]
    al_hydroxide = al_ads * al_ratio
    put("S21", GaOH3=ga_hydroxide, Ga=ga_dissolved, AlOH3=al_hydroxide,
        Na2SO4=m.na2so4,
        Water=total("S14") + total("S20") - ga_hydroxide - ga_dissolved - al_hydroxide - m.na2so4)
    put("S23", GaOH3=m.ga_cake * ga_ratio, AlOH3=m.al_cake * al_ratio, Water=m.cake_h2o)
    s["S22"] = sub("S21", "S23")

    put("S24", NaOH=m.naoh_up9, Water=m.naoh_up9 * (100 / p["NaOHConc"] - 1))
    put("S25", CaO=m.cao)
    put("S25b", Water=m.w_makeup_kg)
    put("S26", Water=m.evap_kg_h * p["OpHours"] / p["CapProd"])
    put("S27", AlOH3=m.al_cake * al_ratio, CaO=m.cao,
        GaOH3=(m.ga_cake - m.ga_elyte) * ga_ratio)
    elyte_total = (total("S23") + total("S24") + total("S25") + total("S25b")
                  - total("S26") - total("S27"))
    put("S28", Ga=m.ga_elyte, NaOH=m.naoh_up9, Water=elyte_total - m.ga_elyte - m.naoh_up9)

    charge_kmol = 3 * (m.ga_crude / p["MGa"]) / (p["EWCE"] / 100)
    oxygen = charge_kmol / 4 * 31.998
    hydrogen = charge_kmol * (1 - p["EWCE"] / 100) / 2 * 2.016
    put("S29", O2=oxygen, H2=hydrogen)
    put("S31", Ga=m.ga_crude)
    s["S30"] = dict(s["S28"])
    s["S30"]["Ga"] -= m.ga_crude
    s["S30"]["Water"] -= oxygen + hydrogen
    s["S30R"] = {k: 0.0 for k in s["S30"]}
    s["S30P"] = dict(s["S30"])
    put("S32", HCl=m.hcl)
    put("S33", Ga=m.ga_crude - m.ga_out["UP11"], HCl=m.hcl)
    put("S34", Ga=m.ga_out["UP11"])

    result = {}
    for sid, components in s.items():
        md = _metadata()[sid]
        result[sid] = {
            **md, "components": components,
            "total_kg_per_kg_Ga": math.fsum(components.values()),
            "Ga": components.get("Ga", 0) + components.get("GaOH3", 0) / ga_ratio,
            "Al": components.get("Al", 0) + components.get("AlOH3", 0) / al_ratio,
            "V": components.get("V", 0),
        }
    return result


def balance_rows(streams):
    """Check the reported total mass and elemental Ga/Al/V at each interface."""
    rows = []
    for unit, (ins, outs) in UNIT_STREAMS.items():
        for label, key in (("Total mass", "total_kg_per_kg_Ga"), ("Ga", "Ga"), ("Al", "Al"), ("V", "V")):
            incoming = math.fsum(streams[sid][key] for sid in ins)
            outgoing = math.fsum(streams[sid][key] for sid in outs)
            residual = incoming - outgoing
            tolerance = max(1e-8, abs(incoming) * 1e-10)
            rows.append({"Unit / boundary": unit, "Quantity": label, "In": incoming,
                         "Out": outgoing, "Residual": residual,
                         "Status": "PASS" if math.isfinite(residual) and abs(residual) <= tolerance else "FAIL"})
    return rows


def stream_issues(streams):
    """Report physically invalid constituents; mass closure alone is insufficient."""
    issues = []
    for sid, record in streams.items():
        for name, value in record["components"].items():
            if not math.isfinite(value) or value < -1e-8:
                issues.append(f"{sid}: {name} = {value:.6g} kg/kg Ga; check process inputs.")
    return issues
