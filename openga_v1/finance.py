"""
openga_v1.finance
=================

Real (constant 2026 AUD) discounted cash flow at a real WACC, the pre-tax
production cost, and the minimum viable price p*.

p* is the closed form of NPV = 0:

    p* = [ FCI + WC(1 - v^n) - S.v^n - PV(grant) - T.PVDEP - PV(CMPTI)
           - PV(concession) + (1-T).OPEX.A ] / [ (1-T).Q.A ]

with A the annuity factor, v^n the end-of-life discount factor, T the tax
rate and Q annual production. The 31-year cash flow is built as well, and
its NPV at p* is the check that the algebra is right.

Nominal historical-cost tax depreciation is deflated by (1+INFL)^-t before
being discounted at the real rate, so a real DCF is not silently credited with
a nominal shield.

p* is the minimum constant real selling price at which the project earns its
cost of capital under the stated assumptions. It is NOT a bankable price, not
a negotiated price and not a forecast.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PolicyValue:
    """Whatever the policy layer contributes to p*, in present-value terms."""
    pv_grant: float = 0.0
    pv_cmpti: float = 0.0
    pv_concession: float = 0.0
    grant_gross: float = 0.0
    grant_net: float = 0.0
    cmpti_annual: float = 0.0
    cmpti_years: int = 0
    cmpti_first_year: int = 0
    depreciable_base_factor: float = 1.0    # multiplies FCI
    real_wacc: float = 0.07
    opex_offset: float = 0.0                # legacy WP4 only
    price_floor: float = 0.0                # legacy WP4 only
    label: str = ""


@dataclass
class FinanceResult:
    real_wacc: float = 0.0
    annuity: float = 0.0
    vn: float = 0.0
    pv_depreciation: float = 0.0
    cash_cost_per_kg: float = 0.0
    capital_charge_per_kg: float = 0.0
    production_cost_per_kg: float = 0.0
    pstar: float = 0.0
    production_cost_usd: float = 0.0
    pstar_usd: float = 0.0
    npv_at_pstar: float = 0.0
    cash_flow: list[dict] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def annuity_factor(r: float, n: float) -> float:
    return (1.0 - (1.0 + r) ** -n) / r if r else n


def pv_depreciation_real(fci: float, life: float, r: float, infl: float) -> float:
    """PV of straight-line tax depreciation on a real basis.

    The deduction is nominal historical cost, so deflating by (1+infl)^-t and
    discounting at the real rate collapses to an annuity at the combined rate.
    """
    combined = (1.0 + r) * (1.0 + infl) - 1.0
    return (fci / life) * annuity_factor(combined, life)


def run(p: dict, fci: float, wc: float, opex_total: float,
        pol: PolicyValue) -> FinanceResult:
    f = FinanceResult()
    r = pol.real_wacc
    n = p["LIFE"]
    T = p["TAXR"]
    Q = p["CapProd"]
    f.real_wacc = r
    f.annuity = annuity_factor(r, n)
    f.vn = (1.0 + r) ** -n

    dep_base = fci * pol.depreciable_base_factor
    f.pv_depreciation = pv_depreciation_real(dep_base, n, r, p["INFL"])

    opex_eff = opex_total * (1.0 - pol.opex_offset)

    f.cash_cost_per_kg = opex_eff / Q
    f.capital_charge_per_kg = (fci + wc * (1 - f.vn) - p["SALV"] * f.vn) / (f.annuity * Q)
    f.production_cost_per_kg = f.cash_cost_per_kg + f.capital_charge_per_kg

    numer = (fci + wc * (1 - f.vn) - p["SALV"] * f.vn
             - pol.pv_grant - T * f.pv_depreciation
             - pol.pv_cmpti - pol.pv_concession
             + (1 - T) * opex_eff * f.annuity)
    denom = (1 - T) * Q * f.annuity
    f.pstar = numer / denom if denom else float("nan")
    if pol.price_floor:
        f.pstar = max(f.pstar, 0.0)

    f.production_cost_usd = f.production_cost_per_kg / p["FX"]
    f.pstar_usd = f.pstar / p["FX"]

    f.cash_flow, f.npv_at_pstar = _cash_flow(p, fci, wc, opex_eff, pol, f)
    return f


def _cash_flow(p, fci, wc, opex_eff, pol: PolicyValue, f: FinanceResult):
    n = int(p["LIFE"])
    T, Q, r = p["TAXR"], p["CapProd"], f.real_wacc
    dep = fci * pol.depreciable_base_factor / n
    rows = []
    npv = 0.0
    for y in range(0, n + 1):
        capex = -(fci + wc) if y == 0 else 0.0
        grant = pol.grant_net if y == int(pol.grant_first_year()) else 0.0
        rev = f.pstar * Q if y >= 1 else 0.0
        op = -opex_eff if y >= 1 else 0.0
        dep_real = dep * (1 + p["INFL"]) ** -y if y >= 1 else 0.0
        taxable = rev + op - dep_real
        tax = -T * taxable if y >= 1 else 0.0
        cmpti = (pol.cmpti_annual
                 if (pol.cmpti_years and pol.cmpti_first_year
                     <= y <= pol.cmpti_first_year + pol.cmpti_years - 1) else 0.0)
        salv = (p["SALV"] + wc) if y == n else 0.0
        ncf = capex + grant + rev + op + tax + cmpti + salv
        df = (1 + r) ** -y
        npv += ncf * df
        rows.append({"year": y, "capex": capex, "grant": grant, "revenue": rev,
                     "opex": op, "depreciation": -dep_real, "tax": tax,
                     "cmpti": cmpti, "salvage": salv, "net": ncf,
                     "discount": df, "pv": ncf * df})
    npv += pol.pv_concession
    return rows, npv


def _grant_first_year(self) -> int:      # attached below, keeps PolicyValue tidy
    return int(self._grant_year)


PolicyValue._grant_year = 0
PolicyValue.grant_first_year = _grant_first_year
