"""
openga_v1.validation
====================

Checks that can actually fail.

Three groups:

``internal``   arithmetic and closure. If one of these fails the model is
               broken, not merely uncertain.
``regression`` reproduction of the source workbook and of the earlier WP3/WP4
               figures. A failure here means the port has drifted.
``divergence`` documented disagreements with the published inventory. These
               are NOT failures. They are the places where this model and Luo
               et al. part company, reported so the difference is visible
               rather than buried.

None of this validates an input. It confirms the arithmetic is internally
consistent and reproduces its source. It cannot tell you whether the feed
assay, the caustic dose, the completeness factor or any emission factor is
right, and most of them are placeholders.
"""

from __future__ import annotations

from dataclasses import dataclass

from .config import ModelInputs, UNIT_OPS
from .engine import Results
from .engine import run as run_engine

# Workbook values at the shipped defaults, OpenGa_v3.3_Carbon.xlsx
V33_TARGETS = {
    "recovery": 0.25814010121445,
    "liquor_t_per_kg": 71.9432141075995,
    "electricity_kwh_kg": 19.8262084394536,
    "isbl_raw": 42821997.7011882,
    "fci": 467616214.896975,
    "cash_cost": 248.010575934145,
    "lcop": 697.398940144556,
    "pstar": 836.669203413946,
    "carbon_total": 32.5958351095836,
    "real_wacc": 0.0877541463414635,
    "pstar_pkg2": 815.769969174314,
    "pstar_pkg3": 698.295970080982,
}

# The uploaded openga_project / WP3-WP4 headline figures. These are reported
# for COMPARISON, never asserted as targets this app must hit: the legacy
# energy mode reinstates WP3's energy allocation on the v3.3 physical basis and
# does not restore WP3's six-stage recovery cascade, so it lands near these
# numbers without reproducing them. Quote them from the WP3/WP4 workbooks.
LEGACY_REFERENCE = {
    "recovery": 0.258361553975,
    "electricity_kwh_kg": 143.558198923213,
    "fci": 494920334.75,
    "lcop": 832.686,
    "pstar": 934.846,
}


@dataclass
class Check:
    group: str
    name: str
    model: float
    reference: float
    tolerance: float
    note: str = ""
    kind: str = "abs"        # "abs" | "rel" | "info"

    @property
    def deviation(self) -> float:
        if self.kind == "rel":
            return self.model / self.reference - 1 if self.reference else float("nan")
        return self.model - self.reference

    @property
    def verdict(self) -> str:
        if self.kind == "info":
            return "n/a"
        return "PASS" if abs(self.deviation) < self.tolerance else "FAIL"


def internal(r: Results) -> list[Check]:
    p = r.params
    out: list[Check] = []
    C = Check

    out.append(C("internal", "Gallium cascade closes on the 1 kg basis",
                 r.meb.ga_out["UP11"], 1.0, 1e-9,
                 "Feed gallium times the eleven recoveries must be exactly one kilogram."))
    out.append(C("internal", "Cost stack ties to the cash operating cost",
                 sum(r.opex.stack_per_kg.values()), r.opex.cash_cost_per_kg, 1e-9,
                 "Every operating line, summed per kilogram."))
    out.append(C("internal", "DCF net present value is zero at p*",
                 r.finance.npv_at_pstar, 0.0, 1.0,
                 "The 31-year cash flow, built independently, must vanish at the closed-form "
                 "p*. Tolerance is one dollar on a project of several hundred million."))
    out.append(C("internal", "Physical allocation closes on every resource",
                 r.allocation.max_residual, 0.0, 1e-9,
                 "Worst residual across all eleven resource columns and the capital share."))
    out.append(C("internal", "Per-unit production cost ties to the headline",
                 sum(v["production"] for v in r.cost_by_up.values()),
                 r.lcop, 1e-8,
                 "If this passes, the per-unit chart is a decomposition of the headline "
                 "number and not a separate estimate that happens to look similar."))
    out.append(C("internal", "Carbon by unit operation ties to an independent recomputation",
                 r.carbon.total, r.carbon.independent_total, 1e-6,
                 "The reference recomputes emissions from MEB plant totals and the blended "
                 "factors, touching none of the allocation."))
    out.append(C("internal", "Scope split adds to the plant total",
                 r.carbon.scope1 + r.carbon.scope2 + r.carbon.upstream,
                 r.carbon.total, 1e-9, "No category counted twice, none dropped."))
    out.append(C("internal", "Electricity mix shares sum to 100%",
                 r.energy.share_sum, 1.0, 1e-9,
                 "Range is checked separately: a mix of 120% grid and minus 20% solar sums "
                 "to 100% and is still invalid."))
    out.append(C("internal", "Electricity mix is valid",
                 1.0 if r.energy.valid else 0.0, 1.0, 1e-9,
                 "Every share between 0 and 100% AND summing to 100%. Nothing is normalised."))
    out.append(C("internal", "Battery round-trip efficiency is in range",
                 1.0 if r.energy.rte_valid else 0.0, 1.0, 1e-9, "Greater than 0, at most 100%."))
    out.append(C("internal", "Gas generator efficiency is in range",
                 1.0 if r.energy.geneff_valid else 0.0, 1.0, 1e-9, "Greater than 0, at most 100%."))
    out.append(C("internal", "Delivered electricity equals process demand",
                 sum(r.energy.delivered_kwh.values()), r.energy.annual_kwh, 1e-4,
                 "Route shares distribute the demand; they do not change it. Battery charging "
                 "energy is reported separately and never added to delivered energy."))
    out.append(C("internal", "A 100% grid mix reproduces the grid reference",
                 r.carbon.total if p["MIX_GRID"] == 1.0 else r.carbon.ref_total,
                 r.carbon.ref_total, 1e-9,
                 "The reference is computed from the grid route alone and does not read the "
                 "selected mix. Passes trivially when a non-grid mix is selected."))
    out.append(C("internal", "Working capital reconciles to operating cost",
                 r.capex.working_capital_aud, p["WCPCT"] * r.opex.total, 1e-6,
                 "One pass, no iteration: variable cost does not depend on ISBL."))
    return out


def regression(mi: ModelInputs) -> list[Check]:
    """Does the port still reproduce its sources?"""
    out: list[Check] = []
    C = Check
    cfg = mi.cfg
    if (cfg.energy_mode == "mechanistic" and cfg.capex_mode == "bottom_up"
            and cfg.policy_model == "v31" and cfg.resin_preset == 1
            and cfg.policy_package == 1
            and mi.resolved() == ModelInputs().resolved()):
        r = run_engine(mi)
        pairs = [
            ("Overall gallium recovery", r.meb.recovery_overall, "recovery", 1e-12),
            ("Liquor throughput, t/kg Ga", r.meb.liquor_t_per_kg, "liquor_t_per_kg", 1e-9),
            ("Electricity intensity, kWh/kg", r.meb.elec_kwh_kg, "electricity_kwh_kg", 1e-9),
            ("Raw bottom-up ISBL, AUD", r.capex.isbl_raw_aud, "isbl_raw", 1e-3),
            ("Fixed capital investment, AUD", r.capex.fci_aud, "fci", 1e-3),
            ("Cash operating cost, AUD/kg", r.opex.cash_cost_per_kg, "cash_cost", 1e-8),
            ("Production cost, AUD/kg", r.lcop, "lcop", 1e-8),
            ("Minimum viable price p*, AUD/kg", r.pstar, "pstar", 1e-8),
            ("Carbon intensity, kg CO2e/kg", r.carbon.total, "carbon_total", 1e-9),
            ("Real WACC", r.finance.real_wacc, "real_wacc", 1e-12),
        ]
        for name, val, key, tol in pairs:
            out.append(C("regression", f"v3.3 workbook: {name}", val, V33_TARGETS[key], tol,
                         "Reproduces OpenGa_v3.3_Carbon.xlsx at the shipped defaults."))
    else:
        out.append(C("regression", "v3.3 workbook regression", 0, 0, 1,
                     "Skipped for this scenario: workbook targets apply only to the shipped "
                     "baseline inputs, mechanistic energy, bottom-up capital, policy package 1 "
                     "and resin preset 1. Internal checks still run on the current scenario.",
                     kind="info"))
    return out


def divergence(r: Results) -> list[Check]:
    """Documented disagreements with the published inventory. Not failures."""
    C = Check
    m = r.meb
    return [
        C("divergence", "Electricity intensity against Luo et al.",
          m.elec_kwh_kg, 102.28, 0, kind="info",
          note="Luo report 102.28 kWh/kg on a Chinese plant with far richer liquor. This "
               "model computes it from duty. The gap is mostly throughput: a weaker assay "
               "means more liquor pumped per kilogram of gallium."),
        C("divergence", "H2SO4 dose against Luo et al.",
          m.h2so4_delivered, 56.0, 0, kind="info",
          note="Luo report 56 kg/kg. This model derives it from eluant bed volumes and resin "
               "turnover, which is a different construction, not a corrected version of "
               "theirs."),
        C("divergence", "UP9 caustic dose against Luo et al.",
          m.naoh_up9, 44.16, 0, kind="info",
          note="Luo report a 44.16 kg/kg gross dose. This model carries the mechanistic "
               "electrolyte make-up instead. It is the single largest operating-cost "
               "uncertainty and the Monte Carlo spans the whole gap."),
        C("divergence", "Published gallium LCA global warming result",
          282.0, 0.0282, 0, kind="info",
          note="Luo et al. 2025 Table 2 prints 2.82e-2 kg CO2e/kg. Their own electricity "
               "line is 102.28 kWh at 1.16 kg CO2e/kWh, or 118.6 kg on its own. Reading the "
               "exponent as +2 gives 282, which puts electricity at 42.1% and matches their "
               "statement that it is 'over 40%'. The published exponent is wrong."),
        C("divergence", "Electricity against the uploaded WP3 model",
          m.elec_kwh_kg, LEGACY_REFERENCE["electricity_kwh_kg"], 0, kind="info",
          note="WP3 reports 143.558 kWh/kg at a 103 mg/L assay. This app's legacy energy "
               "mode reinstates that allocation on the v3.3 physical basis and lands near "
               "but not on it, because it does not also restore WP3's six-stage cascade. "
               "If the exact figure matters, quote it from the WP3 workbook."),
        C("divergence", "Production cost against the uploaded WP4 model",
          r.lcop, LEGACY_REFERENCE["lcop"], 0, kind="info",
          note="WP4 reports A$832.686/kg. That estimate computes capital from gallium "
               "capacity and never sees liquor throughput, which is the defect the v3.0 "
               "rebuild addressed. The two are alternative models, not versions of one."),
        C("divergence", "Raw bottom-up capital against the published comparable",
          r.capex.raw_share_of_reference, 1.0, 0, kind="info",
          note=f"The itemised list costs out at {r.capex.raw_share_of_reference * 100:.0f}% "
               f"of the Wesselkaemper comparable. A completeness factor of "
               f"{r.capex.completeness_required:.1f} would reconcile them; the model applies "
               f"{r.capex.completeness_factor:g}. This is the weakest part of the estimate "
               "and it is shown rather than hidden."),
    ]


def run_all(mi: ModelInputs) -> dict[str, list[Check]]:
    r = run_engine(mi)
    return {"internal": internal(r), "regression": regression(mi), "divergence": divergence(r)}


def summary(groups: dict[str, list[Check]]) -> dict[str, str]:
    out = {}
    for g, checks in groups.items():
        real = [c for c in checks if c.kind != "info"]
        if not real:
            out[g] = f"0 of 0 ({len(checks)} informational)"
            continue
        passed = sum(1 for c in real if c.verdict == "PASS")
        out[g] = f"{passed} of {len(real)}"
    return out
