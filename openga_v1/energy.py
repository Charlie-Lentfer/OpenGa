"""
openga_v1.energy
================

Electricity supply mix and the blended price and emission factors it implies.

Five routes, each a share of electricity DELIVERED TO THE PROCESS. Each share
must sit between 0% and 100% and the five must sum to exactly 100%. Nothing is
normalised: an invalid mix is reported as invalid, not quietly fixed.

Everything is stated per kWh delivered, so the blend is a plain dot product.
Generator efficiency and battery round-trip losses are applied ONCE, here,
when each delivered value is derived, and never again downstream.

Scope discipline
----------------
Grid is purchased: scope 2, with network losses reported separately as scope 3.
Behind-the-meter solar and direct-connected wind are neither purchased nor
combusted: no scope 1, no scope 2, embodied manufacturing only. Onsite gas is
combusted at the boundary: scope 1, with upstream fuel supply separate. No
total lifecycle factor is ever added on top of an operational factor that
already contains it.

This is an annual energy balance. It tests nothing about hourly dispatch,
generation capacity, curtailment, firming or battery sizing. A 100% direct
solar mix is arithmetically valid here and physically impossible for a
continuous process.
"""

from __future__ import annotations

from dataclasses import dataclass, field

ROUTES = [
    ("grid", "Grid electricity", "MIX_GRID"),
    ("solar", "Direct behind-the-meter solar", "MIX_SOLAR"),
    ("solbat", "Solar through battery storage", "MIX_SOLBAT"),
    ("wind", "Dedicated direct-connected wind", "MIX_WIND"),
    ("gas", "Onsite natural-gas generation", "MIX_GAS"),
]


@dataclass
class Route:
    key: str
    name: str
    share: float
    price: float          # AUD/MWh delivered
    ef_s1: float          # kg CO2e/kWh delivered
    ef_s2: float
    ef_up: float
    status: str
    confidence: str
    boundary: str
    source: str


@dataclass
class EnergyResult:
    routes: list[Route] = field(default_factory=list)
    share_sum: float = 0.0
    valid: bool = True
    invalid_reason: str = ""
    rte_valid: bool = True
    geneff_valid: bool = True
    rte_used: float = 1.0
    geneff_used: float = 1.0
    storage_cost: float = 0.0
    ef_batt: float = 0.0
    mix_price: float = 0.0
    mix_ef_s1: float = 0.0
    mix_ef_s2: float = 0.0
    mix_ef_up: float = 0.0
    grid_price: float = 0.0
    grid_ef_total: float = 0.0
    annual_kwh: float = 0.0
    delivered_kwh: dict[str, float] = field(default_factory=dict)
    charging_kwh: float = 0.0
    active_price: float = 0.0
    use_mix: bool = False
    notes: list[str] = field(default_factory=list)

    @property
    def mix_ef_total(self) -> float:
        return self.mix_ef_s1 + self.mix_ef_s2 + self.mix_ef_up


def run(p: dict, elec_kwh_per_kg: float) -> EnergyResult:
    r = EnergyResult()

    # --- guards. Both efficiencies sit in denominators; an out-of-range value
    #     substitutes 100% so the model stays readable and the flag goes up.
    rte, geneff = p["RTE"], p["GENEFF"]
    r.rte_valid = 0.0 < rte <= 1.0
    r.geneff_valid = 0.0 < geneff <= 1.0
    r.rte_used = rte if r.rte_valid else 1.0
    r.geneff_used = geneff if r.geneff_valid else 1.0
    if not r.rte_valid:
        r.notes.append("Battery round-trip efficiency is outside 0-100%. Running at 100% so "
                       "the numbers render; every battery figure is meaningless until you "
                       "fix it.")
    if not r.geneff_valid:
        r.notes.append("Gas generator efficiency is outside 0-100%. Running at 100%; every "
                       "gas figure is meaningless until you fix it.")

    # --- derived route values, each computed once
    r.storage_cost = p["BATT_CAPEX"] * 1000.0 / (p["BATT_CYC"] * p["BATT_DOD"])
    r.ef_batt = p["BATT_MFG"] / (p["BATT_CYC"] * p["BATT_DOD"])
    pe_gas = p["GASPRICE"] * 3.6 / r.geneff_used + p["GENOM"]
    ef_gas_s1 = p["EF_GAS"] * 3.6 / 1000.0 / r.geneff_used
    ef_gas_up = p["GAS_S3_GJ"] * 3.6 / 1000.0 / r.geneff_used
    pe_solbat = p["PE_SOLAR"] / r.rte_used + r.storage_cost
    ef_solbat_up = p["EFS_UP"] / r.rte_used + r.ef_batt
    pe_grid = p["P_ELEC_BASE"]

    r.routes = [
        Route("grid", "Grid electricity", p["MIX_GRID"], pe_grid,
              0.0, p["EF_ELEC"], p["EF_ELEC_S3"], "CITED", "High",
              "Purchased: scope 2 location-based, network losses as scope 3.",
              "NGA Factors 2025 (DCCEEW), WA SWIS. Price linked to the model base."),
        Route("solar", "Direct behind-the-meter solar", p["MIX_SOLAR"], p["PE_SOLAR"],
              0.0, 0.0, p["EFS_UP"], "ESTIMATE", "Low",
              "Not purchased, not combusted: embodied manufacturing only.",
              "Embodied 40 g/kWh inside the published 18-180 g range (Energies 2025 "
              "18(24):6413). Price is an estimate below the Lu et al. PV+BESS figure."),
        Route("solbat", "Solar through battery storage", p["MIX_SOLBAT"], pe_solbat,
              0.0, 0.0, ef_solbat_up, "DERIVED", "Low",
              "Solar grossed up for round-trip loss plus battery embodied per kWh "
              "discharged. Charging energy counted once.",
              "Round-trip 88%, manufacturing 100 kg CO2e/kWh capacity over 5,000 cycles at "
              "90% DoD (GJETA 2025). Storage cost from GenCost battery capex on the same "
              "throughput basis, excluding cost of capital, so it is a floor."),
        Route("wind", "Dedicated direct-connected wind", p["MIX_WIND"], p["PE_WIND"],
              0.0, 0.0, p["EFW_UP"], "ESTIMATE", "Low",
              "Direct connection, not a PPA or certificate: no scope 2.",
              "Embodied 12 g/kWh inside the published 7-56 g range (Energies 2025). Price "
              "estimated inside the CSIRO GenCost band, which is a GENERATION price and not "
              "a delivered tariff."),
        Route("gas", "Onsite natural-gas generation", p["MIX_GAS"], pe_gas,
              ef_gas_s1, 0.0, ef_gas_up, "DERIVED from CITED", "Med",
              "Combusted at the boundary: scope 1, upstream fuel supply separate.",
              "NGA Factors 2025 Table 5 combustion 51.53 kg CO2e/GJ and Table 6 WA non-metro "
              "upstream 4.0 kg CO2e/GJ, at 3.6 GJ/MWh over the generator efficiency."),
    ]

    shares = [rt.share for rt in r.routes]
    r.share_sum = sum(shares)
    in_range = all(0.0 <= s <= 1.0 for s in shares)
    sums_to_one = abs(r.share_sum - 1.0) < 1e-9
    r.valid = in_range and sums_to_one
    if not r.valid:
        bits = []
        if not sums_to_one:
            bits.append(f"the shares sum to {r.share_sum * 100:.2f}%, not 100%")
        if not in_range:
            bits.append("at least one share is outside 0-100%")
        r.invalid_reason = ("Invalid mix: " + " and ".join(bits)
                            + ". Nothing is normalised, so every blended figure below is "
                              "wrong until you fix it.")

    r.mix_price = sum(rt.share * rt.price for rt in r.routes)
    r.mix_ef_s1 = sum(rt.share * rt.ef_s1 for rt in r.routes)
    r.mix_ef_s2 = sum(rt.share * rt.ef_s2 for rt in r.routes)
    r.mix_ef_up = sum(rt.share * rt.ef_up for rt in r.routes)
    r.grid_price = pe_grid
    r.grid_ef_total = p["EF_ELEC"] + p["EF_ELEC_S3"]

    r.annual_kwh = elec_kwh_per_kg * p["CapProd"]
    r.delivered_kwh = {rt.key: r.annual_kwh * rt.share for rt in r.routes}
    r.charging_kwh = r.delivered_kwh["solbat"] / r.rte_used

    r.use_mix = bool(p["USEMIX"] == 1)
    r.active_price = r.mix_price if r.use_mix else p["P_ELEC_BASE"]
    return r
