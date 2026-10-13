"""
openga_v1.policy
================

Two policy models, selectable.

``v31`` — the v3.1 module
    CAPM cost of equity, a blended cost of debt, a concessional facility valued
    over its ACTUAL tenor rather than the project life, CMPTI as a refundable
    offset on eligible operating expenditure, and a capital grant with an
    explicit tax treatment.

    Two mutually exclusive ways to value a concessional loan:
      FINMODE 1  blend the supported rate into Kd, so it shows up in the WACC
      FINMODE 2  take the PV of after-tax interest savings on the declining
                 balance, discounted at the commercial cost of debt (APV)
    Doing both double-counts. Mode 2 is the default because a 15-year facility
    on a 30-year plant is not a permanent discount rate, and mode 1 applies it
    for all 30 years.

``legacy`` — the WP4 three-scenario model
    An OPEX offset, a WACC case and a price floor. Kept so the earlier figures
    reproduce.

None of these packages is a government commitment. They are scenario labels.
Export Finance Australia publishes no universal rate, no grant programme has
committed anything, and the grant's tax treatment would need a ruling.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .config import LEGACY_POLICY_SCENARIOS, LEGACY_WACC, PolicyPackage
from .finance import PolicyValue, annuity_factor


@dataclass
class FinancingBuildUp:
    ke: float = 0.0
    kd_commercial: float = 0.0
    kd_blended: float = 0.0
    kd_in_wacc: float = 0.0
    beta_levered: float = 0.0
    wacc_nominal: float = 0.0
    wacc_real: float = 0.0
    debt_equity: float = 0.0


@dataclass
class PolicyResult:
    model: str = "v31"
    label: str = ""
    financing: FinancingBuildUp = field(default_factory=FinancingBuildUp)
    net_funding: float = 0.0
    debt_raised: float = 0.0
    equity_raised: float = 0.0
    supported_debt: float = 0.0
    commercial_debt: float = 0.0
    concession_schedule: list[dict] = field(default_factory=list)
    value: PolicyValue = field(default_factory=PolicyValue)
    notes: list[str] = field(default_factory=list)


def financing(p: dict, conc_share: float, supported_rate: float | None) -> FinancingBuildUp:
    f = FinancingBuildUp()
    gear = p["GEAR"]
    f.debt_equity = gear / (1 - gear) if gear < 1 else float("inf")
    f.beta_levered = p["BETA_U"] * (1 + (1 - p["TAXR"]) * f.debt_equity)
    f.ke = p["RFR"] + f.beta_levered * p["MRP"]
    f.kd_commercial = p["RFR"] + p["KD_MARGIN"] + p["KD_FEES"]
    rate = supported_rate if supported_rate is not None else f.kd_commercial
    f.kd_blended = (1 - conc_share) * f.kd_commercial + conc_share * rate
    # FINMODE 2 (default) values the concession separately, so the WACC must
    # keep the COMMERCIAL rate or the benefit is counted twice.
    f.kd_in_wacc = f.kd_blended if p["FINMODE"] == 1 else f.kd_commercial
    f.wacc_nominal = (1 - gear) * f.ke + gear * f.kd_in_wacc * (1 - p["TAXR"])
    if p["WACCMODE"] == 1:
        f.wacc_real = p["R_WACC_LEG"]
    else:
        f.wacc_real = (1 + f.wacc_nominal) / (1 + p["INFL"]) - 1
    return f


def run_v31(p: dict, pkg: PolicyPackage, fci: float, wc: float,
            opex_total: float, eligible_opex: float) -> PolicyResult:
    r = PolicyResult(model="v31", label=pkg.name)
    r.financing = financing(p, pkg.conc_share, pkg.supported_rate)
    rr = r.financing.wacc_real
    v = r.value
    v.real_wacc = rr
    v.label = pkg.name

    # --- capital, grant, funding
    v.grant_gross = fci * pkg.grant_pct
    v.grant_net = v.grant_gross * (1 - p["TAXR"] * p["GRANT_ASSESS"])
    v._grant_year = int(p["GRANT_YR"])
    v.pv_grant = v.grant_net * (1 + rr) ** -p["GRANT_YR"]
    v.depreciable_base_factor = 1.0 - pkg.grant_pct * p["GRANT_REDBASE"]

    r.net_funding = fci + wc - v.grant_gross
    r.debt_raised = r.net_funding * p["GEAR"]
    r.equity_raised = r.net_funding * (1 - p["GEAR"])
    r.supported_debt = r.debt_raised * pkg.conc_share
    r.commercial_debt = r.debt_raised * (1 - pkg.conc_share)

    # --- concessional benefit over the ACTUAL tenor, not the project life
    if p["FINMODE"] == 2 and r.supported_debt > 0:
        tenor = int(p["TENOR"])
        kd_comm = r.financing.kd_commercial
        rate = pkg.supported_rate if pkg.supported_rate is not None else kd_comm
        bal = r.supported_debt
        amort = r.supported_debt / tenor if p["REPAY"] == 1 else 0.0
        pv = 0.0
        for y in range(1, int(p["LIFE"]) + 1):
            if y <= tenor:
                saving = bal * (kd_comm - rate) * (1 - p["TAXR"])
                df = (1 + kd_comm) ** -y
                pv += saving * df
                r.concession_schedule.append(
                    {"year": y, "balance": bal, "saving": saving, "pv": saving * df})
                bal = max(0.0, bal - amort) if p["REPAY"] == 1 else (0.0 if y == tenor else bal)
            else:
                r.concession_schedule.append(
                    {"year": y, "balance": 0.0, "saving": 0.0, "pv": 0.0})
        v.pv_concession = pv
        r.notes.append(
            f"Concession valued over its {tenor}-year tenor, not the {int(p['LIFE'])}-year "
            "plant life, and discounted at the commercial cost of debt. FINMODE 2.")
    elif p["FINMODE"] == 1:
        r.notes.append(
            "FINMODE 1: the supported rate is blended into the WACC and applied for the whole "
            "project life. That overstates a finite facility, which is why mode 2 is the "
            "default. The concession is NOT also valued separately here — that would "
            "double-count.")

    # --- CMPTI
    if pkg.cmpti_on and pkg.cmpti_years:
        v.cmpti_annual = pkg.cmpti_rate * eligible_opex
        v.cmpti_years = int(min(pkg.cmpti_years, p["CMPTI_MAXYRS"]))
        v.cmpti_first_year = 1
        lag = p["CMPTI_LAG"]
        v.pv_cmpti = (v.cmpti_annual * annuity_factor(rr, v.cmpti_years)
                      * (1 + rr) ** -(v.cmpti_first_year - 1 + lag))
        r.notes.append(
            f"CMPTI at {pkg.cmpti_rate * 100:.0f}% of eligible operating expenditure "
            f"(A${eligible_opex:,.0f}/yr) for {v.cmpti_years} years. Capital, financing, "
            "feedstock and decline-in-value are excluded by statute.")
    return r


def run_legacy(p: dict, scenario_id: int, opex_total: float) -> PolicyResult:
    sc = next(s for s in LEGACY_POLICY_SCENARIOS if s.id == scenario_id)
    r = PolicyResult(model="legacy", label=sc.name)
    v = r.value
    v.real_wacc = LEGACY_WACC[sc.wacc_case]
    v.opex_offset = sc.opex_offset
    v.price_floor = sc.price_floor
    v.label = sc.name
    r.financing.wacc_real = v.real_wacc
    r.notes.append(sc.note)
    if sc.opex_offset:
        r.notes.append(
            "The offset is applied to TOTAL operating cost and held constant for the full "
            "life. Both are simplifications carried from WP4: the statute excludes several "
            "cost categories and caps the claim period.")
    if sc.price_floor:
        r.notes.append(
            f"A price floor of A${sc.price_floor:,.0f}/kg de-risks revenue but does not enter "
            "the p* algebra, which already solves for the price that clears the hurdle. It is "
            "shown for comparison against p*, not fed back into it.")
    return r


# CMPTI eligibility, line by line. The fraction is what the register asserts,
# not what the ATO has confirmed for a gallium flowsheet — none of this has
# been tested.
ELIGIBILITY: dict[str, tuple[float, str]] = {
    "Sulfuric acid (98% w/w)": (1.0, "Reagent. DISR lists reagents as eligible direct "
                                     "processing expenditure."),
    "Caustic soda (100% basis)": (1.0, "Reagent."),
    "Quicklime": (1.0, "Reagent."),
    "Hydrochloric acid": (1.0, "Reagent."),
    "Ion exchange resin make-up": (1.0, "Consumable media, expensed as make-up rather than "
                                        "capitalised. If it were capitalised its decline in "
                                        "value would be expressly excluded."),
    "Electricity": (1.0, "Utility. DISR lists utilities as eligible."),
    "Steam": (1.0, "Utility."),
    "Process water": (1.0, "Utility."),
    "Bayer liquor feedstock": (0.0, "EXPRESSLY EXCLUDED. The ATO lists feedstock among "
                                    "excluded expenditure."),
    "Water treatment reject disposal": (1.0, "Waste treatment and disposal, named as eligible "
                                             "by DISR."),
    "Solid residue disposal": (1.0, "Waste treatment and disposal."),
    "Operating labour": (1.0, "Labour, named as eligible by DISR."),
    "Maintenance": (0.5, "PROVISIONAL SPLIT. Routine maintenance is operating expenditure and "
                         "eligible; sustaining capital is not. Half is a placeholder for a "
                         "split nobody has tested."),
    "Insurance, rates and administration": (0.0, "Conservative exclusion: indirect, not "
                                                 "processing expenditure."),
    "Plant overhead": (0.0, "Conservative exclusion, same reasoning. This line is itself a "
                            "factor on labour and maintenance, so including it would double "
                            "count them."),
}


def eligibility_register(opex_variable: dict, opex_fixed: dict) -> list[dict]:
    rows = []
    for name, cost in list(opex_variable.items()) + list(opex_fixed.items()):
        frac, basis = ELIGIBILITY.get(name, (0.0, "Not classified — excluded by default."))
        rows.append({"line": name, "cost": cost, "fraction": frac,
                     "eligible": cost * frac, "basis": basis})
    return rows


def eligible_opex(p: dict, opex_variable: dict, opex_fixed: dict) -> float:
    return sum(r["eligible"] for r in eligibility_register(opex_variable, opex_fixed))
