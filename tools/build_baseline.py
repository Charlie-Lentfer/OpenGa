"""
tools/build_baseline.py
=======================
Regenerate tests/baseline.json from the source-of-truth workbooks by reading
their CACHED (recalculated) values with openpyxl (data_only=True).

Run after any change to WP3_Balance_v3_3.xlsx or Ga_Financial_Model_WP4_v2.xlsx:

    python tools/build_baseline.py --wp3 path/to/WP3_Balance_v3_3.xlsx \\
                                   --wp4 path/to/Ga_Financial_Model_WP4_v2.xlsx

The workbooks themselves are NOT shipped in the repo (they are the author's
working files); this script is the documented bridge between them and the
Python regression baseline.
"""
from __future__ import annotations

import argparse
import json
import os

try:
    import openpyxl
except ImportError:  # pragma: no cover
    openpyxl = None


def _cells(path, sheet, coords):
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb[sheet]
    return {c: ws[c].value for c in coords}


def build(wp3: str, wp4: str) -> dict:
    b = {"_source": {"wp3": os.path.basename(wp3), "wp4": os.path.basename(wp4)}}

    # ---- MEB (WP3) --------------------------------------------------------
    summ = _cells(wp3, "SUMMARY", ["B21", "G16", "H16", "D16"])
    exp = _cells(wp3, "UP_EXPORT",
                 ["B17", "C17", "D17", "E17", "F17", "G17", "H17", "I17", "J17", "K17"])
    b["meb"] = {
        "throughput_t": summ["B21"], "electricity_kwh": summ["G16"],
        "thermal_kwh": summ["H16"], "overall_recovery": summ["D16"],
        "steam_kg": exp["C17"], "h2so4_kg": exp["D17"], "naoh_kg": exp["E17"],
        "cao_kg": exp["F17"], "hcl_kg": exp["G17"], "resin_kg": exp["H17"],
        "fresh_water_kg": exp["I17"], "salty_reject_kg": exp["J17"],
        "solid_residue_kg": exp["K17"],
    }

    # ---- CARBON (WP3) -----------------------------------------------------
    car = _cells(wp3, "CARBON", ["E17", "F17", "I6"])
    b["carbon"] = {"s1_s2": car["E17"], "with_embodied": car["F17"],
                   "luo_gwp_china_grid": car["I6"]}

    # ---- FINANCE (WP4) ----------------------------------------------------
    capex = _cells(wp4, "CAPEX", ["B38", "B40"])
    opex = _cells(wp4, "OPEX", ["F16", "F20", "F21", "F24"])
    dep = _cells(wp4, "DEPREC", ["H35"])
    lcop = _cells(wp4, "LCOP", ["B17", "B18"])
    up = _cells(wp4, "UPCOST", ["M5"])  # sanity
    b["finance"] = {
        "fci": capex["B38"], "working_capital": capex["B40"],
        "opex_variable": opex["F16"], "opex_fixed": opex["F20"],
        "opex_total": opex["F21"], "cmpti_eligible_base": opex["F24"],
        "pv_depreciation": dep["H35"], "lcop_pretax": lcop["B17"], "mvp": lcop["B18"],
    }

    # ---- VALIDATION (WP4 WESS_REP) ---------------------------------------
    w = _cells(wp4, "WESS_REP", ["B70", "B74", "B71", "B72", "B73"])
    b["wesselkaemper"] = {
        "lcop_base": w["B70"], "capital_component": w["B74"],
        "lcop_s1": w["B71"], "lcop_s2": w["B72"], "lcop_grant": w["B73"],
        "targets": {"base": 421.98, "capital": 240.71, "s1": 663.97,
                    "s2": 568.11, "grant": 291.60},
    }

    # ---- BREAKEVEN (WP4) --------------------------------------------------
    be = _cells(wp4, "BREAKEVEN", ["F14", "F19"])
    b["breakeven"] = {"50": be["F14"], "100": be["F19"]}
    return b


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--wp3", required=True)
    ap.add_argument("--wp4", required=True)
    ap.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "..", "tests", "baseline.json"))
    a = ap.parse_args()
    if openpyxl is None:
        raise SystemExit("openpyxl required: pip install openpyxl")
    data = build(a.wp3, a.wp4)
    with open(a.out, "w") as fh:
        json.dump(data, fh, indent=2)
    print("wrote", os.path.abspath(a.out))


if __name__ == "__main__":
    main()
