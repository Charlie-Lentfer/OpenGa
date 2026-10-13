"""
openga_v1.config
================

Every input the model takes, in one place, with the metadata the UI needs to
present it honestly: label, unit, category, source, evidence status and
confidence.

Defaults are generated from ``OpenGa_v3.3_Carbon.xlsx`` (see ``_gen_defaults``)
so the app and the workbook cannot drift apart by transcription.

Design note
-----------
The model is a flat parameter dictionary, not a tree of dataclasses. That
sounds crude but it is deliberate: there are ~230 inputs, the UI needs to
enumerate and group them generically, and the override machinery then reduces
to ``{**defaults, **user}``. Structure lives in ``CATEGORIES`` below, which is
presentation metadata, not calculation state.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ._gen_defaults import V33_DEFAULTS

# ---------------------------------------------------------------------------
# Structural switches — these change WHICH equations run, not just their inputs
# ---------------------------------------------------------------------------

ENERGY_MODES = {
    "mechanistic": "v3.3 mechanistic — pumping from rho.g.Q.H/eta, electrowinning from Faraday",
    "legacy_wp3": "Legacy WP3 — Luo allocation scaled by throughput / resin / hardness ratios",
}

CAPEX_MODES = {
    "bottom_up": "Bottom-up — 16 items sized off the MEB, Towler & Sinnott correlations",
    "six_tenths": "Six-tenths scaling — a comparable plant's capital scaled on Ga capacity",
    "user_total": "User total — your own FCI and the capacity it corresponds to",
    "per_stage": "Per stage — eleven installed costs, one per unit operation",
}

POLICY_MODELS = {
    "v31": "v3.1 module — CAPM cost of equity, concessional debt valued over its tenor, CMPTI, capital grant",
    "legacy": "Legacy WP4 — three scenarios: OPEX offset, WACC case, price floor",
}

UNIT_OPS = [
    ("UP1", "Filter press"),
    ("UP2", "Ion exchange"),
    ("UP3", "Washing"),
    ("UP4", "Softening / acid make-up"),
    ("UP5", "Elution"),
    ("UP6", "Regeneration"),
    ("UP7", "Precipitation"),
    ("UP8", "Centrifuge"),
    ("UP9", "Purification"),
    ("UP10", "Electrowinning"),
    ("UP11", "Refining"),
]

# ---------------------------------------------------------------------------
# Input categories — how the UI groups the flat parameter dictionary
# Each entry: (tab group, human title, ordered list of keys)
# ---------------------------------------------------------------------------

CATEGORIES: list[tuple[str, str, list[str]]] = [
    ("Plant basis", "Capacity, hours and life", [
        "CapProd", "OpHours", "LIFE"]),
    ("Plant basis", "Feed liquor chemistry", [
        "GaFeed", "VFeed", "AlFeed", "LiqDensity", "SSLoad", "ImpRatio"]),
    ("Process", "Recovery cascade, UP1 to UP11", [
        "FiltCakeMoist", "IXRec", "WashRec", "EluEff", "PrecRec", "CentRec",
        "PurRec", "EWRec", "RefYield"]),
    ("Process", "Ion exchange performance", [
        "IXRec", "CoAdsV", "CoAdsAl", "ResinCap", "ResinBulk", "ResinLife"]),
    ("Process", "Reagent doses and strengths", [
        "WashBV", "EluBV", "EluStrength", "AcidPurity", "RegenBV", "NaOHConc",
        "NaOHTrim", "CakeMoist", "NaOH_UP9", "CaODose", "HClDose"]),
    ("Process", "Electrowinning and electrolyte", [
        "ElecGa", "ElecNaOH", "ElecDens", "EWVolt", "EWCE"]),
    ("Process", "Energy and duty", [
        "PumpHead", "WashHead", "PumpEff", "EvapEcon", "SteamLatent", "MiscElec"]),
    ("Equipment", "Sizing parameters", [
        "IXVel", "IXBed", "IXColLoad", "IXColTot", "FiltFlux", "ReactRes",
        "VesFill", "TankDays", "EvapU", "EvapDT", "CentCap", "CentDia",
        "EWRes", "SoftReject"]),
    ("Equipment", "Costing allowances", [
        "VesThk", "SteelDens", "HeadAllow", "MiscEquip", "SparePct",
        "EWRectCost", "RESINCAPEX"]),
    ("Capital", "Escalation, location and currency", [
        "CEPCI_B", "CEPCI_N", "LOCFAC", "FX", "MatFac"]),
    ("Capital", "Installation and factorial build-up", [
        "HandPump", "HandVes", "HandHX", "HandMisc", "OSBLPCT", "ENGPCT",
        "CONTPCT", "WCPCT", "CAPFAC"]),
    ("Capital", "Comparable plant (six-tenths mode)", [
        "RefCapex", "RefCap", "ScaleExp"]),
    ("Operating cost", "Unit prices", [
        "P_ELEC_BASE", "P_STEAM", "P_H2SO4", "P_NAOH", "P_CAO", "P_HCL",
        "P_RESIN", "P_WATER", "P_SALTY", "P_SOLID", "P_FEED"]),
    ("Operating cost", "Fixed cost", [
        "P_LABOUR", "N_LABOUR", "F_MAINT", "F_INS", "F_OVER"]),
    ("Finance", "Tax, inflation and salvage", [
        "TAXR", "INFL", "SALV"]),
    ("Finance", "Cost of capital", [
        "WACCMODE", "R_WACC_LEG", "RFR", "MRP", "BETA_U", "GEAR",
        "KD_MARGIN", "KD_FEES"]),
    ("Finance", "Concessional debt", [
        "FINMODE", "KD_CONC", "TENOR", "REPAY"]),
    ("Policy", "Package selector", [
        "POLSEL"]),
    ("Policy", "CMPTI", [
        "CMPTI_RATE_STAT", "CMPTI_MAXYRS", "CMPTI_LAG"]),
    ("Policy", "Capital grant", [
        "GRANT_YR", "GRANT_ASSESS", "GRANT_REDBASE"]),
    ("Policy", "Offtake assessment", [
        "OT_COV", "OT_YRS", "OT_IDX", "OT_PM"]),
    ("Energy mix", "Delivered shares", [
        "MIX_GRID", "MIX_SOLAR", "MIX_SOLBAT", "MIX_WIND", "MIX_GAS"]),
    ("Energy mix", "Route prices", [
        "PE_SOLAR", "PE_WIND", "GASPRICE", "GENEFF", "GENOM"]),
    ("Energy mix", "Battery storage", [
        "RTE", "BATT_CAPEX", "BATT_CYC", "BATT_DOD", "BATT_MFG"]),
    ("Energy mix", "Financial connection", [
        "USEMIX"]),
    ("Carbon", "Electricity and fuel factors", [
        "EF_ELEC", "EF_ELEC_S3", "EF_GAS", "BOILEFF", "GAS_S3_GJ"]),
    ("Carbon", "Renewable and battery embodied factors", [
        "EFS_UP", "EFW_UP"]),
    ("Carbon", "Embodied chemical and waste factors", [
        "EF_NAOH", "EF_H2SO4", "EF_CAO", "EF_HCL", "EF_RESIN", "EF_WATER",
        "EF_REJECT", "EF_SOLID", "EF_FEED", "EF_NA2SO4"]),
    ("Carbon", "Allocation", [
        "AL_LIQ1"]),
]

# Keys that are integer-valued selectors rather than continuous quantities.
SELECTOR_KEYS = {
    "RESINSEL": [1, 2, 3, 4],
    "POLSEL": [1, 2, 3, 4],
    "CPXMETH": [1, 2],
    "WACCMODE": [1, 2],
    "FINMODE": [1, 2],
    "REPAY": [1, 2],
    "USEMIX": [0, 1],
    "GRANT_ASSESS": [0, 1],
    "GRANT_REDBASE": [0, 1],
    "OT_IDX": [1, 2],
    "RESINCAPEX": [0, 1],
}

# Keys expressed as a fraction in the model but naturally shown as a percentage.
PERCENT_KEYS = {
    "MIX_GRID", "MIX_SOLAR", "MIX_SOLBAT", "MIX_WIND", "MIX_GAS",
    "RTE", "BATT_DOD", "GENEFF", "TAXR", "INFL", "GEAR", "OSBLPCT",
    "ENGPCT", "CONTPCT", "WCPCT", "F_MAINT", "F_INS", "F_OVER",
    "R_WACC_LEG", "RFR", "MRP", "KD_MARGIN", "KD_FEES", "KD_CONC",
    "SoftReject", "AL_LIQ1", "OT_COV", "CMPTI_RATE_STAT", "VesFill",
}


# ---------------------------------------------------------------------------
# Resin preset library (v3.2 Inputs section 21)
# ---------------------------------------------------------------------------

@dataclass
class ResinPreset:
    id: int
    name: str
    ga_recovery_pct: float
    v_coads_pct: float
    al_coads_pct: float
    capacity_mg_g: float
    status: str
    note: str


RESIN_PRESETS: list[ResinPreset] = [
    ResinPreset(
        1, "TY-CH550, Gorzin optimised (BASE CASE)", 31.7, 7.8, 0.1, 26.9, "COMPOSITE",
        "Recovery and co-adsorption from Gorzin et al. on TY-CH550 (R5); working capacity "
        "26.9 mg/g from Zhao et al. 2016 for LSC-700 (R3). A COMPOSITE of two studies, not "
        "one characterised product."),
    ResinPreset(
        2, "Amidoxime chelating resin", 78.3, 15.16, 6.63, 26.9, "CITED (capacity carried)",
        "Materials 2024, 17(16), 4109 (R12). Working capacity is NOT reported in that paper "
        "and is carried at the base value. The 6.63% Al co-adsorption is 66x the base case "
        "and drives the purification duty — check the precipitate grade before believing it."),
    ResinPreset(
        3, "High working capacity variant, base kinetics", 31.7, 7.8, 0.1, 55.0, "BOUND",
        "Zhao et al. 2016 quote capacities up to 55 mg/g for this class. Recovery held at "
        "base so the preset isolates one variable. Column diameter is set by superficial "
        "velocity and does not move; resin inventory and bed-volume turnover both halve, "
        "which drags wash, eluant, regeneration and stoichiometric caustic down with them."),
    ResinPreset(
        4, "Custom — your own vendor or pilot data", 31.7, 7.8, 0.1, 26.9, "USER",
        "Overwrite the four values and record your source."),
]


def get_resin_preset(pid: int) -> ResinPreset:
    for p in RESIN_PRESETS:
        if p.id == pid:
            return p
    raise KeyError(f"no resin preset {pid}")


# ---------------------------------------------------------------------------
# Policy packages (v3.1 Inputs section 14)
# ---------------------------------------------------------------------------

@dataclass
class PolicyPackage:
    id: int
    name: str
    grant_pct: float        # fraction of gross FCI
    conc_share: float       # fraction of total debt on supported terms
    supported_rate: float | None   # None -> commercial rate
    cmpti_on: int
    cmpti_rate: float
    cmpti_years: int
    note: str


def default_policy_packages(d: dict) -> list[PolicyPackage]:
    rate = d["CMPTI_RATE_STAT"]
    conc = d["KD_CONC"]
    return [
        PolicyPackage(1, "No policy support", 0.0, 0.0, None, 0, rate, 0,
                      "Merchant project on commercial terms."),
        PolicyPackage(2, "Medium support", 0.0, 0.5, conc, 1, rate, 10,
                      "Half the debt on supported terms plus CMPTI. No grant."),
        PolicyPackage(3, "Bullish support", 0.25, 1.0, conc, 1, rate, 10,
                      "25% capital grant, all debt supported, CMPTI. The grant is the "
                      "purely hypothetical lever and it does most of the work."),
        PolicyPackage(4, "Custom", 0.0, 0.0, None, 0, rate, 0,
                      "Yours to set."),
    ]


# ---------------------------------------------------------------------------
# Legacy WP4 policy scenarios (from the uploaded openga_project)
# ---------------------------------------------------------------------------

@dataclass
class LegacyPolicyScenario:
    id: int
    name: str
    opex_offset: float
    wacc_case: int          # 1 low, 2 base, 3 high
    price_floor: float
    note: str


LEGACY_POLICY_SCENARIOS = [
    LegacyPolicyScenario(1, "Baseline (no policy support)", 0.0, 2, 0.0,
                         "Merchant project, market finance, no offtake support."),
    LegacyPolicyScenario(2, "CMPTI + EFA facility financing", 0.10, 1, 0.0,
                         "10% refundable offset on eligible processing OPEX, held constant "
                         "over the full life. Concessional debt via the low WACC case."),
    LegacyPolicyScenario(3, "CMSR offtake guarantee", 0.0, 2, 600.0,
                         "Price floor de-risks revenue; modelled as MAX(price, floor)."),
]

LEGACY_WACC = {1: 0.045, 2: 0.07, 3: 0.095}


# ---------------------------------------------------------------------------
# The parameter set the engine actually consumes
# ---------------------------------------------------------------------------

RESIN_INPUTS = {
    "IXRec": (RESIN_PRESETS[0].ga_recovery_pct, "UP2 Ga recovery by ion exchange", "%"),
    "CoAdsV": (RESIN_PRESETS[0].v_coads_pct, "Vanadium co-adsorption", "%"),
    "CoAdsAl": (RESIN_PRESETS[0].al_coads_pct, "Aluminium co-adsorption", "%"),
    "ResinCap": (RESIN_PRESETS[0].capacity_mg_g, "Resin working capacity", "mg/g"),
}


def base_params() -> dict[str, float]:
    """Workbook defaults plus the existing baseline resin preset's four values."""
    return {**{k: spec[0] for k, spec in V33_DEFAULTS.items()},
            **{k: spec[0] for k, spec in RESIN_INPUTS.items()}}


def meta(key: str) -> dict[str, Any]:
    if key in RESIN_INPUTS:
        val, label, unit = RESIN_INPUTS[key]
        return {"default": val, "label": label, "unit": unit, "row": None,
                "status": "COMPOSITE", "conf": "Inherited",
                "source": RESIN_PRESETS[0].note + " Editable when the Custom resin preset is selected."}
    spec = V33_DEFAULTS.get(key)
    if spec is None:
        return {"label": key, "unit": "-", "status": "-", "conf": "-", "source": ""}
    val, label, unit, row, status, conf, src = spec
    return {"default": val, "label": label, "unit": unit, "row": row,
            "status": status, "conf": conf, "source": src}


@dataclass
class CapexUserTotal:
    """CAPEX mode 3 — the user supplies a whole-plant number and its capacity."""
    fci_aud: float = 467_616_215.0
    capacity_t_yr: float = 100.0
    scaling_exponent: float = 0.6
    note: str = "Your own estimate. Scaled to the model capacity on the stated exponent."


@dataclass
class CapexPerStage:
    """CAPEX mode 4 — eleven INSTALLED costs, one per unit operation, summing to ISBL.

    Installed means delivered, erected and connected: OSBL, engineering and
    contingency are applied on top to reach FCI. It does NOT mean bare
    equipment, and it does NOT mean a share of FCI.
    """
    values: dict[str, float] = field(default_factory=lambda: {u: 0.0 for u, _ in UNIT_OPS})
    note: str = "Installed cost per unit operation. Sums to ISBL; factors apply on top."


@dataclass
class ModelConfig:
    """Structural switches. Everything else is a number in ``params``."""
    energy_mode: str = "mechanistic"
    capex_mode: str = "bottom_up"
    policy_model: str = "v31"
    resin_preset: int = 1
    policy_package: int = 1
    legacy_policy: int = 1
    capex_user: CapexUserTotal = field(default_factory=CapexUserTotal)
    capex_stage: CapexPerStage = field(default_factory=CapexPerStage)


@dataclass
class ModelInputs:
    params: dict[str, float] = field(default_factory=base_params)
    cfg: ModelConfig = field(default_factory=ModelConfig)

    def with_overrides(self, overrides: dict[str, float] | None) -> "ModelInputs":
        if not overrides:
            return self
        p = dict(self.params)
        p.update({k: v for k, v in overrides.items() if k in p or k in V33_DEFAULTS})
        return ModelInputs(params=p, cfg=self.cfg)

    def resolved(self) -> dict[str, float]:
        """Params with the resin preset applied, unless the user picked Custom."""
        p = dict(self.params)
        preset = get_resin_preset(self.cfg.resin_preset)
        if preset.id != 4:
            p["IXRec"] = preset.ga_recovery_pct
            p["CoAdsV"] = preset.v_coads_pct
            p["CoAdsAl"] = preset.al_coads_pct
            p["ResinCap"] = preset.capacity_mg_g
        return p
