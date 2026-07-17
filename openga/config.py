"""
openga.config
=============
Single source of default parameters for the OpenGa techno-economic model.

Every value is transcribed from the two source-of-truth workbooks:

    WP3_Balance_v3_3.xlsx      (mass & energy balance)  -> INPUTS / REF / RESINS / CARBON_EF
    Ga_Financial_Model_WP4_v2.xlsx (financial model)    -> PRICES / CAPEX / FIN / POLICY / NORM

The workbooks remain the *authoritative* record; this module reproduces their
cached values so the Python model can be regression-tested against them
(`tests/baseline.json`).

Citations mirror the WP3 REF register (R1-R12) and each row's confidence /
data-gap flag.  Use `citation(field)` to resolve any parameter to its source.

Nothing here performs calculation.  Derived quantities live in `openga.meb`
and `openga.finance`.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace, asdict
from typing import Dict, Tuple

# ---------------------------------------------------------------------------
# REF register  (WP3 REF sheet)
# ---------------------------------------------------------------------------
REF: Dict[str, Dict[str, str]] = {
    "R1":  {"cite": "Luo et al. 2025, LCA of gallium recovery from Bayer liquor (CC-BY)",
            "conf": "High (published LCI)"},
    "R2":  {"cite": "Lu et al. 2017 - elution efficiency 95%/30min; eluant 4% w/w H2SO4",
            "conf": "High"},
    "R3":  {"cite": "Zhao et al. 2016, ACS Sust. Chem. Eng., doi:10.1021/acssuschemeng.5b00307 "
                    "- resin working capacity 26.9 mg Ga/g", "conf": "Med"},
    "R4":  {"cite": "Xu et al. 2024 - EW ~9 kWh/kg, 99.993% purity; electrolyte 39.9 g/L Ga / 120 g/L NaOH",
            "conf": "High"},
    "R5":  {"cite": "Gorzin - IX single-pass Ga 31.7%; V co-adsorption 7.8% (TY-CH550)",
            "conf": "Med"},
    "R6":  {"cite": "WP2 process flowsheet (this thesis) - unit descriptions, cake moisture, grades, yields",
            "conf": "Med"},
    "R7":  {"cite": "Jajarm plant characterisation - feed proxy Ga 103 mg/L, V 149.6 mg/L",
            "conf": "Med (PROXY - single most critical data gap)"},
    "R8":  {"cite": "Alcoa-Sojitz Wagerup JV - 100 t/yr capacity target", "conf": "Med"},
    "R9":  {"cite": "Engineering assumption (this work)", "conf": "Low"},
    "R10": {"cite": "Industry data request pending (Alcoa/Rio/South32/CSIRO)", "conf": "-"},
    "R11": {"cite": "Stoichiometry / physical constants (CRC)", "conf": "High"},
    "R12": {"cite": "Materials 2024, 17(16), 4109, doi:10.3390/ma17164109 - amidoxime resin",
            "conf": "Med (published)"},
    # WP4 supplementary references
    "W1":  {"cite": "Wesselkaemper et al. 2025, Resour. Conserv. Recycl., doi:10.1016/j.resconrec.2025.108436",
            "conf": "High (published TEA)"},
    "W2":  {"cite": "Peters, Timmerhaus & West - TEA factors (six-tenths rule, Lang factor, maintenance/insurance)",
            "conf": "High"},
    "W3":  {"cite": "Lu et al. 2026, Solar Energy 303 - onsite PV+BESS vs WA industrial supply",
            "conf": "Cited (range)"},
    "W4":  {"cite": "ATO - CMPTI / Div 419 / corporate tax; EFA concessional finance", "conf": "Statutory"},
    "PH":  {"cite": "PLACEHOLDER - replace with sourced value before results are quoted", "conf": "Low"},
}

# citation registry: field name -> (ref_id, data_gap?)
CITATIONS: Dict[str, Tuple[str, bool]] = {}


def _c(ref_id: str, gap: bool = False):
    """Decorator-free helper: record a citation for a field name at import."""
    return (ref_id, gap)


def citation(field_name: str) -> Dict[str, str]:
    """Resolve a config field to its full source record."""
    ref_id, gap = CITATIONS.get(field_name, ("?", False))
    rec = dict(REF.get(ref_id, {"cite": "unknown", "conf": "-"}))
    rec.update(ref=ref_id, data_gap=gap)
    return rec


# ---------------------------------------------------------------------------
# Physical / chemical constants  (WP3 INPUTS C01-C07, R11)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Constants:
    M_Ga: float = 69.723        # C01
    M_NaOH: float = 39.997      # C02
    M_H2SO4: float = 98.079     # C03
    M_Na2SO4: float = 142.04    # C04
    Faraday: float = 96485.0    # C05  (C/mol)
    M_Al: float = 26.982        # C06
    M_OH: float = 17.008        # C07


# ---------------------------------------------------------------------------
# Resin preset library  (WP3 RESINS sheet).  Index 1..4 (Excel INDEX order).
# columns: Ga single-pass %, V co-ads %, Al co-ads %, working capacity mg Ga/g
# ---------------------------------------------------------------------------
RESINS: Dict[int, Dict[str, float]] = {
    1: {"name": "TY-CH550 (base case)",     "ga": 31.70, "v": 7.80,  "al": 0.10, "cap": 26.9, "ref": "R5"},
    2: {"name": "Amidoxime chelating",      "ga": 78.30, "v": 15.16, "al": 6.63, "cap": 26.9, "ref": "R12"},
    3: {"name": "Custom (vendor/pilot)",    "ga": 31.70, "v": 7.80,  "al": 0.10, "cap": 26.9, "ref": "user"},
    4: {"name": "Luo baseline (implied)",   "ga": 41.59, "v": 15.16, "al": 0.10, "cap": 26.9, "ref": "R1"},
}


# ---------------------------------------------------------------------------
# INPUTS  (WP3 INPUTS sheet).  Two scenario columns collapse to the ACTIVE
# value at construction: scenario 1 -> Luo baseline (D), 2 -> plant/custom (E).
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class MebInputs:
    # switches ---------------------------------------------------------------
    resin_preset: int = 1          # INPUTS F3  (1..4)
    scenario: int = 2              # INPUTS F4  (1=Luo validation, 2=Australian)

    # global basis -----------------------------------------------------------
    cap_prod: float = 100_000.0    # P01 kg Ga/yr   [R8]
    op_hours: float = 8_000.0      # P02 h/yr       [R9]

    # feed liquor (ACTIVE = scenario-2 Australian defaults) -------------------
    ga_feed: float = 103.0         # P03 mg/L  (Luo baseline D = 230)  [R7]
    ga_feed_luo: float = 230.0     # INPUTS D11 (validation reference)
    v_feed: float = 149.6          # P04 mg/L  [R7]
    v_feed_luo: float = 149.6      # INPUTS D12
    al_feed: float = 50.0          # P05 g/L   [R9]
    liq_density: float = 1.3       # P06 kg/L  [R9]
    liq_temp: float = 50.0         # P07 degC  [R6]
    ss_load: float = 2.0           # P08 kg/t  [R1]

    # site water -------------------------------------------------------------
    hard_ref: float = 150.0        # P09 mg/L CaCO3 [R9]
    hard_site: float = 80.0        # P10 mg/L CaCO3 (Luo baseline D = 150) [R9]
    imp_ratio: float = 1.0         # P11 impurity load ratio [R9]

    # UP3 wash / UP4-5 acid --------------------------------------------------
    wash_base: float = 1860.0      # P16 kg/kg [R1]
    acid_base: float = 56.0        # P17 kg/kg 98% H2SO4 [R1]
    acid_purity: float = 98.0      # P18 %     [R1]
    elu_strength: float = 4.0      # P19 % w/w [R2]
    raw_water_luo: float = 1.56    # P20 info only [R1]
    salty_base: float = 365.0      # P21 kg/kg [R1]
    g1_base: float = 0.000688      # P22 kg/kg [R1]
    elu_eff: float = 95.0          # P23 %     [R2]

    # UP6 regeneration -------------------------------------------------------
    resin_dose: float = 3.0        # P24 kg/kg [R6]
    regen_water: float = 30.9      # P25 kg/kg [R1]
    regen_naoh: float = 0.0        # P26 kg/kg [R9]

    # UP7 precipitation ------------------------------------------------------
    naoh_trim: float = 0.0         # P27 kg/kg [R9]
    naoh_conc: float = 32.0        # P28 % w/w [R1]
    naoh_ref7: float = 44.84       # P29 Luo UP7 dose (validation ref) [R1]

    # UP8 centrifuge ---------------------------------------------------------
    cent_rec: float = 98.0         # P30 %     [R6]
    cake_moist: float = 40.0       # P31 %     [R6]
    prec_grade: float = 28.0       # P32 % (reference cross-check only) [R6]

    # UP9 purification -------------------------------------------------------
    pur_rec: float = 95.0          # P33 %     [R9]
    naoh_mode: int = 1             # P34 1=Luo gross, 2=mechanistic
    naoh_ref9: float = 44.16       # P35 Luo UP9 dose [R1]
    cao_base: float = 2.0          # P36 kg/kg [R1]
    cake_base: float = 2.4         # P37 kg/kg [R1]
    cond_ref: float = 32.25        # P38 condensate allocation (Luo) [R1]
    ga_elec: float = 39.9          # P39 electrolyte Ga g/L (ref only) [R4]
    naoh_elec: float = 120.0       # P40 electrolyte NaOH g/L (ref only) [R4]
    ele_dens: float = 1.15         # P41 kg/L  [R9]
    evap_econ: float = 1.0         # P42       [R9]
    steam_latent: float = 2.26     # P43 MJ/kg [R11]

    # UP10 electrowinning ----------------------------------------------------
    ew_rec: float = 95.0           # P44 %     [R9]
    ew_volt: float = 2.4           # P45 V     [R6]
    ew_ce: float = 47.9            # P46 %     [R6]

    # UP11 refining ----------------------------------------------------------
    ref_yield: float = 97.0        # P47 %     [R6]
    hcl_dose: float = 0.012        # P48 kg/kg [R9]
    grade_in: float = 99.9         # P49 %     [R6]
    grade_out: float = 99.99       # P50 %     [R6]

    # Luo 102.28 kWh/kg energy allocations (E01-E16) -------------------------
    e_up1: float = 17.23           # x RatioT
    e_up2: float = 11.39           # x RatioT
    e_up3: float = 3.27            # x RatioResin
    e_up4g: float = 9.0            # fixed
    e_up4a: float = 0.72           # x RatioResin
    e_up4s: float = 1.35           # x RatioHard
    e_up5g: float = 4.55           # fixed
    e_up5c: float = 26.1           # x RatioResin
    e_up6: float = 1.98            # fixed
    e_up7g: float = 4.75           # fixed
    e_up7c: float = 1.81           # x NaOH ratio
    e_up8: float = 0.0             # grouped with UP7
    e_up9g: float = 13.27          # fixed
    e_up9c: float = 1.81           # x NaOH ratio
    e_up10ref: float = 3.86        # Luo allocation (ref only; model uses Faraday)
    e_up11: float = 0.29           # fixed

    const: Constants = field(default_factory=Constants)

    # ---- scenario resolution ----------------------------------------------
    def active(self) -> "MebInputs":
        """
        Return a copy with feed-profile fields resolved for the active
        scenario (mirrors INPUTS =IF($F$4=1,D,E)).  In the workbook only the
        feed Ga concentration (230 vs 103 mg/L) and site hardness (150 vs
        80 mg/L) differ between the Luo (D) and plant (E) columns; every other
        row shares its D/E value.  Resin-derived rows (P12-P15) follow the
        preset in *both* scenarios and are handled by the ix_rec etc. props.
        """
        if self.scenario == 1:  # Luo baseline / validation column
            return replace(self, ga_feed=self.ga_feed_luo, hard_site=self.hard_ref)
        return self

    # resin-derived rows (P12-P15) always follow the preset in both scenarios
    @property
    def ix_rec(self) -> float:      # P12
        return RESINS[self.resin_preset]["ga"]

    @property
    def co_ads_v(self) -> float:    # P13
        return RESINS[self.resin_preset]["v"]

    @property
    def co_ads_al(self) -> float:   # P14
        return RESINS[self.resin_preset]["al"]

    @property
    def resin_cap(self) -> float:   # P15
        return RESINS[self.resin_preset]["cap"]


# ---------------------------------------------------------------------------
# CARBON_EF  (WP3 CARBON_EF sheet).  ALL VALUES PLACEHOLDER.
# scope tag: "S1" (scope 1), "S2" (scope 2), "embodied".
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class EmissionFactor:
    value: float
    unit: str
    scope: str
    confidence: str
    source: str


@dataclass(frozen=True)
class CarbonEF:
    grid_elec_au: EmissionFactor = EmissionFactor(
        0.51, "kg CO2e/kWh", "S2", "LOW-PLACEHOLDER",
        "DCCEEW NGA Factors (SWIS for WA hosts). Cite year+table.")
    grid_elec_cn: EmissionFactor = EmissionFactor(
        0.58, "kg CO2e/kWh", "S2", "LOW-PLACEHOLDER",
        "Luo SI / ecoinvent CN grid (validation only).")
    steam: EmissionFactor = EmissionFactor(
        0.14, "kg CO2e/kg", "S1", "LOW-PLACEHOLDER", "Gas boiler, NGA fuel combustion.")
    naoh: EmissionFactor = EmissionFactor(
        1.12, "kg CO2e/kg", "embodied", "LOW-PLACEHOLDER", "ecoinvent chlor-alkali (membrane).")
    h2so4: EmissionFactor = EmissionFactor(
        0.12, "kg CO2e/kg", "embodied", "LOW-PLACEHOLDER", "ecoinvent sulfuric acid, contact.")
    cao: EmissionFactor = EmissionFactor(
        1.10, "kg CO2e/kg", "embodied", "LOW-PLACEHOLDER", "ecoinvent quicklime.")
    hcl: EmissionFactor = EmissionFactor(
        0.90, "kg CO2e/kg", "embodied", "LOW-PLACEHOLDER", "Minor line.")
    resin: EmissionFactor = EmissionFactor(
        6.00, "kg CO2e/kg", "embodied", "LOW-PLACEHOLDER", "Polymer proxy pending resin LCI.")
    fresh_water: EmissionFactor = EmissionFactor(
        0.0003, "kg CO2e/kg", "embodied", "LOW-PLACEHOLDER", "Treatment + pumping ~0.3 kg/kL.")
    salty_reject: EmissionFactor = EmissionFactor(
        0.001, "kg CO2e/kg", "embodied", "LOW-PLACEHOLDER", "Handling/transport allowance.")
    solid_residue: EmissionFactor = EmissionFactor(
        0.02, "kg CO2e/kg", "embodied", "LOW-PLACEHOLDER", "Landfill handling allowance.")


# ---------------------------------------------------------------------------
# PRICES  (WP4 PRICES sheet).  AUD, real 2026.  (low, base, high)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class PriceRange:
    low: float
    base: float
    high: float
    unit: str
    status: str


@dataclass(frozen=True)
class Prices:
    electricity: PriceRange = PriceRange(92, 157, 200, "$/MWh", "CITED (range) [W3]")
    steam: PriceRange = PriceRange(25, 45, 70, "$/t", "PLACEHOLDER")
    h2so4: PriceRange = PriceRange(150, 250, 400, "$/t", "PLACEHOLDER")
    naoh: PriceRange = PriceRange(500, 800, 1100, "$/t", "PLACEHOLDER")
    cao: PriceRange = PriceRange(200, 300, 450, "$/t", "PLACEHOLDER")
    hcl: PriceRange = PriceRange(300, 500, 800, "$/t", "PLACEHOLDER")
    resin: PriceRange = PriceRange(8, 15, 25, "$/kg", "PLACEHOLDER")
    water: PriceRange = PriceRange(1, 2.5, 4, "$/kL", "PLACEHOLDER")
    salty_disposal: PriceRange = PriceRange(5, 20, 50, "$/t", "PLACEHOLDER")
    residue_disposal: PriceRange = PriceRange(50, 150, 300, "$/t", "PLACEHOLDER")
    feedstock: PriceRange = PriceRange(0, 0, 0, "$/t", "ASSUMPTION (co-located, $0)")
    labour: PriceRange = PriceRange(150000, 180000, 220000, "$/FTE-yr", "PLACEHOLDER")
    headcount: PriceRange = PriceRange(12, 16, 24, "FTE", "PLACEHOLDER")
    maint_pct: PriceRange = PriceRange(0.02, 0.03, 0.04, "of FCI/yr", "CITED (factor) [W2]")
    insurance_pct: PriceRange = PriceRange(0.01, 0.015, 0.02, "of FCI/yr", "CITED (factor) [W2]")


# ---------------------------------------------------------------------------
# NORM  (WP4 NORM sheet).  Single conversion point.
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Norm:
    fx_usd_aud: float = 1.52       # AUD/USD  [PLACEHOLDER]
    fx_eur_aud: float = 1.65       # AUD/EUR  [PLACEHOLDER]
    cepci_ref: float = 800.0       # 2024 index  [PLACEHOLDER]
    cepci_val: float = 820.0       # 2026 index  [PLACEHOLDER]

    @property
    def cepci_fac(self) -> float:
        return self.cepci_val / self.cepci_ref


# ---------------------------------------------------------------------------
# CAPEX  (WP4 CAPEX sheet)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class CapexInputs:
    method: int = 1                # 1 = top-down six-tenths, 2 = bottom-up factored
    ref_capex_usd_m: float = 221.55        # US$M  (implied from Wesselkaemper) [W1]
    ref_capacity_t: float = 76.61          # t Ga/yr  [W1]
    scaling_exponent: float = 0.6          # six-tenths rule  [W2]
    location_factor: float = 1.25          # USGC -> AU  [PLACEHOLDER]
    lang_factor: float = 4.74              # fluid processing plant  [W2]
    wc_pct: float = 0.15                   # working capital % of annual OPEX  [PLACEHOLDER]


# ---------------------------------------------------------------------------
# FIN  (WP4 FIN sheet)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class FinInputs:
    tax_rate: float = 0.30         # ATO corporate  [W4]
    life: int = 30                 # years
    deprec_method: int = 1         # 1 = SL, 2 = DV
    salvage: float = 0.0
    wacc_low: float = 0.045        # concessional / EFA  [PLACEHOLDER]
    wacc_base: float = 0.070       # merchant           [PLACEHOLDER]
    wacc_high: float = 0.095       # risk-weighted      [PLACEHOLDER]

    @property
    def dv_rate(self) -> float:
        return 2.0 / self.life


# ---------------------------------------------------------------------------
# POLICY  (WP4 POLICY sheet).  Each scenario: (opex_offset, wacc_case, price_floor)
# wacc_case: 1=low, 2=base, 3=high.
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class PolicyScenario:
    name: str
    opex_offset: float
    wacc_case: int
    price_floor: float
    note: str


POLICY_SCENARIOS: Dict[int, PolicyScenario] = {
    1: PolicyScenario("Baseline (no policy support)", 0.0, 2, 0.0,
                      "Merchant project, market finance, no offtake support."),
    2: PolicyScenario("CMPTI + EFA facility financing", 0.10, 1, 0.0,
                      "10% refundable offset on eligible OPEX (ATO CMPTI); concessional EFA -> low WACC."),
    3: PolicyScenario("CMSR offtake guarantee", 0.0, 2, 600.0,
                      "Price floor de-risks revenue/bankability. PLACEHOLDER floor from WP1 ladder."),
}


# ---------------------------------------------------------------------------
# LADDER  (WP4 LADDER sheet).  WP1 price benchmarks (USD/kg PLACEHOLDER).
# ---------------------------------------------------------------------------
PRICE_LADDER_USD: Dict[str, float] = {
    "SMM China domestic 4N": 265.0,
    "China FOB": 425.0,
    "Ex-China institutional spot": 595.0,
}


# ---------------------------------------------------------------------------
# WESSELKAEMPER replication parameters  (WP4 WESS_REP sheet, 2024 USD)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class WessParams:
    capex_usd_m: float = 222.0             # SI published  [W1]
    cap_share_y0: float = 0.15             # 15/70/15 schedule
    cap_share_y1: float = 0.70
    cap_share_y2: float = 0.15
    discount_rate: float = 0.07            # SI Table 2.1
    nameplate_kg: float = 76_610.0
    prod_start_year: int = 3
    productive_years: int = 30             # years 3..32
    decom_pct: float = 0.10
    decom_year: int = 33
    var_opex_per_kg: float = 90.52         # 88.54 consumables + 1.98 utilities
    fixed_opex_per_kg_nameplate: float = 90.75
    us_demand_2023_kg: float = 19_000.0
    demand_anchor: int = 1                 # 1 = calendar t0=2023 ; 2 = production start
    cagr_s1: float = 0.065
    cagr_s2: float = 0.095
    grant_usd_m: float = 120.0

    # published targets (US$/kg) for the regression tests
    target_base: float = 421.98
    target_capital: float = 240.71
    target_s1: float = 663.97
    target_s2: float = 568.11
    target_grant: float = 291.60


# ---------------------------------------------------------------------------
# Aggregate configuration object
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Config:
    meb: MebInputs = field(default_factory=MebInputs)
    ef: CarbonEF = field(default_factory=CarbonEF)
    prices: Prices = field(default_factory=Prices)
    norm: Norm = field(default_factory=Norm)
    capex: CapexInputs = field(default_factory=CapexInputs)
    fin: FinInputs = field(default_factory=FinInputs)
    wess: WessParams = field(default_factory=WessParams)

    def with_(self, **overrides) -> "Config":
        """Return a copy with top-level sub-configs replaced, e.g. cfg.with_(fin=...)"""
        return replace(self, **overrides)


DEFAULT = Config()

__all__ = [
    "REF", "citation", "Constants", "RESINS", "MebInputs", "CarbonEF", "EmissionFactor",
    "Prices", "PriceRange", "Norm", "CapexInputs", "FinInputs", "PolicyScenario",
    "POLICY_SCENARIOS", "PRICE_LADDER_USD", "WessParams", "Config", "DEFAULT", "asdict",
]
