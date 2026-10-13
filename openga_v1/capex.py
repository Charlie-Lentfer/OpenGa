"""
openga_v1.capex
===============

Four ways to arrive at fixed capital. They are alternatives, not refinements
of each other, and they disagree — which is the honest state of a first-of-a-
kind plant with no built comparable.

1. ``bottom_up``   Sixteen items sized off the MEB and costed with Towler &
                   Sinnott correlations, escalated on CEPCI, converted at the
                   location factor and FX, then multiplied by a visible
                   equipment-list completeness factor. The completeness factor
                   exists because the itemised list covers major process
                   equipment only and costs out at roughly one sixth of the
                   published comparable. Hiding that gap inside a fudged
                   correlation would be worse than showing it.
2. ``six_tenths``  A comparable plant's capital scaled on gallium capacity at
                   the six-tenths rule, with a location factor and FX.
3. ``user_total``  Your own FCI and the capacity it belongs to, scaled to the
                   model capacity on a stated exponent.
4. ``per_stage``   Eleven INSTALLED costs, one per unit operation, summing to
                   ISBL. OSBL, engineering and contingency then apply on top.

Every mode lands on the same downstream quantity — ISBL — so the factorial
build-up to FCI is shared and the comparison is like for like.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .config import UNIT_OPS
from .equipment import EquipResult


@dataclass
class CapexResult:
    mode: str = "bottom_up"
    isbl_correlated_aud: float = 0.0
    isbl_direct_aud: float = 0.0
    isbl_raw_aud: float = 0.0
    completeness_factor: float = 1.0
    isbl_aud: float = 0.0
    osbl_aud: float = 0.0
    engineering_aud: float = 0.0
    contingency_aud: float = 0.0
    fci_aud: float = 0.0
    working_capital_aud: float = 0.0
    tci_aud: float = 0.0
    isbl_by_up: dict[str, float] = field(default_factory=dict)
    # benchmarks
    fci_raw_aud: float = 0.0
    fci_reference_aud: float = 0.0
    raw_share_of_reference: float = 0.0
    completeness_required: float = 0.0
    intensity_usd_k_per_t: float = 0.0
    notes: list[str] = field(default_factory=list)


def _factorial(p: dict, isbl: float, opex_total: float, r: CapexResult) -> None:
    r.isbl_aud = isbl
    r.osbl_aud = isbl * p["OSBLPCT"]
    base = isbl + r.osbl_aud
    r.engineering_aud = base * p["ENGPCT"]
    r.contingency_aud = base * p["CONTPCT"]
    r.fci_aud = isbl + r.osbl_aud + r.engineering_aud + r.contingency_aud
    r.working_capital_aud = p["WCPCT"] * opex_total
    r.tci_aud = r.fci_aud + r.working_capital_aud


def run(p: dict, eq: EquipResult, opex_total: float, mode: str,
        user_total=None, per_stage=None, meb_liquor_m3h: float = 0.0) -> CapexResult:
    r = CapexResult(mode=mode)
    esc = p["CEPCI_N"] / p["CEPCI_B"]

    # --- correlated ISBL in AUD is needed by every mode's benchmark block
    inst_loc_usd = eq.installed_usd2010 * esc * p["LOCFAC"]
    r.isbl_correlated_aud = inst_loc_usd * p["FX"]
    r.isbl_direct_aud = eq.direct_aud
    r.isbl_raw_aud = r.isbl_correlated_aud + r.isbl_direct_aud

    if mode == "bottom_up":
        r.completeness_factor = p["CAPFAC"] if p["CPXMETH"] == 2 else 1.0
        isbl = r.isbl_raw_aud * r.completeness_factor
        # share out by unit operation on installed-cost share of the itemised list
        tot = sum(eq.installed_by_up.values())
        if tot:
            for up, _ in UNIT_OPS:
                share = eq.installed_by_up.get(up, 0.0) / tot
                r.isbl_by_up[up] = share * r.isbl_correlated_aud
            # the two directly priced items go to their own unit
            r.isbl_by_up["UP2"] = r.isbl_by_up.get("UP2", 0.0) + eq.resin_charge_aud
            r.isbl_by_up["UP10"] = r.isbl_by_up.get("UP10", 0.0) + eq.rectifier_aud
            # the completeness factor scales the whole plant uniformly, so it
            # multiplies every unit's share after the directs are added, not
            # before — otherwise the two directly priced items escape it.
            for up, _ in UNIT_OPS:
                r.isbl_by_up[up] *= r.completeness_factor
        if r.completeness_factor != 1.0:
            r.notes.append(
                f"A completeness factor of {r.completeness_factor:g} is applied. The itemised "
                "list covers major process equipment only; raw, it costs out at about one "
                "sixth of the published comparable. Read the benchmark block before quoting "
                "any capital number.")

    elif mode == "six_tenths":
        isbl_equiv = (p["RefCapex"] * 1e6 * (p["CapProd"] / 1000.0 / p["RefCap"]) ** p["ScaleExp"]
                      * p["LOCFAC"] * p["FX"])
        # the comparable is quoted as total capital, so back out ISBL through
        # the same factorial chain rather than treating it as ISBL directly
        chain = (1 + p["OSBLPCT"]) * (1 + p["ENGPCT"] + p["CONTPCT"])
        isbl = isbl_equiv / chain
        r.notes.append(
            f"Scaled from a comparable plant at US${p['RefCapex']:.0f}M for "
            f"{p['RefCap']:.2f} t/yr on the six-tenths rule, then divided back through the "
            "OSBL, engineering and contingency chain so the factorial build-up is not "
            "applied twice.")
        _share_by_up(eq, r, isbl)

    elif mode == "user_total":
        fci_user = user_total.fci_aud
        cap_user_kg = user_total.capacity_t_yr * 1000.0
        if cap_user_kg > 0:
            fci_scaled = fci_user * (p["CapProd"] / cap_user_kg) ** user_total.scaling_exponent
        else:
            fci_scaled = fci_user
        chain = (1 + p["OSBLPCT"]) * (1 + p["ENGPCT"] + p["CONTPCT"])
        isbl = fci_scaled / chain
        r.notes.append(
            f"Your FCI of A${fci_user:,.0f} at {user_total.capacity_t_yr:g} t/yr, scaled to "
            f"{p['CapProd'] / 1000:g} t/yr on an exponent of {user_total.scaling_exponent:g}, "
            "then divided back through the factorial chain so those factors are not applied "
            "on top of a number that already contains them.")
        _share_by_up(eq, r, isbl)

    elif mode == "per_stage":
        vals = per_stage.values
        isbl = sum(vals.get(u, 0.0) for u, _ in UNIT_OPS)
        r.isbl_by_up = {u: vals.get(u, 0.0) for u, _ in UNIT_OPS}
        if isbl <= 0:
            r.notes.append(
                "Every stage is zero, so ISBL is zero and every capital-derived number below "
                "is meaningless. Enter installed costs on the CAPEX tab.")
        else:
            r.notes.append(
                "Eleven installed costs summing to ISBL. OSBL, engineering and contingency "
                "are applied on top. Nothing here is sized from the MEB, so changing the feed "
                "assay will no longer move your capital.")
    else:
        raise ValueError(f"unknown capex mode {mode!r}")

    _factorial(p, isbl, opex_total, r)

    # ---------------------------------------------------------- benchmarks
    chain = (1 + p["OSBLPCT"]) * (1 + p["ENGPCT"] + p["CONTPCT"])
    r.fci_raw_aud = r.isbl_raw_aud * chain
    r.fci_reference_aud = (p["RefCapex"] * 1e6
                           * (p["CapProd"] / 1000.0 / p["RefCap"]) ** p["ScaleExp"]
                           * p["LOCFAC"] * p["FX"])
    if r.fci_reference_aud:
        r.raw_share_of_reference = r.fci_raw_aud / r.fci_reference_aud
    if r.fci_raw_aud:
        r.completeness_required = r.fci_reference_aud / r.fci_raw_aud
    if p["CapProd"]:
        r.intensity_usd_k_per_t = r.fci_aud / p["FX"] / (p["CapProd"] / 1000.0) / 1000.0
    return r


def _share_by_up(eq: EquipResult, r: CapexResult, isbl: float) -> None:
    """Distribute a top-down ISBL across unit operations on the itemised
    installed-cost share. It is the only defensible split available when the
    capital number did not come from an equipment list."""
    tot = sum(eq.installed_by_up.values())
    if not tot:
        return
    for up, _ in UNIT_OPS:
        r.isbl_by_up[up] = eq.installed_by_up.get(up, 0.0) / tot * isbl
    r.notes.append(
        "The per-unit capital split uses the itemised equipment list's shares, because a "
        "top-down capital number carries no information about where the money sits.")
