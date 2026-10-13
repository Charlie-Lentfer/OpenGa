#!/usr/bin/env python3
"""Run the model without Streamlit and print the check suite.

    python3 selftest.py

Use this to confirm the engine is intact before a presentation, or to get the
headline numbers without opening the interface.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from openga_v1 import analysis, config, engine, validation
from openga_v1.streams import balance_rows, stream_issues


def main() -> int:
    mi = config.ModelInputs()
    r = engine.run(mi)

    print("OpenGa V2 — baseline run\n" + "=" * 62)
    for label, value, unit in [
        ("Overall gallium recovery", r.meb.recovery_overall * 100, "%"),
        ("Liquor throughput", r.meb.liquor_t_per_kg, "t/kg Ga"),
        ("Electricity intensity", r.meb.elec_kwh_kg, "kWh/kg Ga"),
        ("Fixed capital investment", r.capex.fci_aud / 1e6, "AUD M"),
        ("Cash operating cost", r.opex.cash_cost_per_kg, "AUD/kg"),
        ("Production cost", r.lcop, "AUD/kg"),
        ("Minimum viable price p*", r.pstar, "AUD/kg"),
        ("Carbon intensity, all boundaries", r.carbon.total, "kg CO2e/kg"),
        ("Carbon intensity, scope 1+2", r.carbon.scope12, "kg CO2e/kg"),
        ("Real WACC", r.finance.real_wacc * 100, "%"),
    ]:
        print(f"  {label:<36s} {value:>16,.6f}  {unit}")

    print("\nPolicy packages\n" + "-" * 62)
    for row in engine.scenario_sweep(mi):
        print(f"  {row['id']}  {row['name']:<24s} p* {row['pstar']:>10,.2f}"
              f"   reduction {row['reduction']:>8,.2f}  ({row['reduction_pct']:>6.2%})")

    groups = validation.run_all(mi)
    summary = validation.summary(groups)
    print("\nChecks\n" + "-" * 62)
    for g, s in summary.items():
        print(f"  {g:<12s} {s}")

    failures = [c for cs in groups.values() for c in cs if c.verdict == "FAIL"]
    for c in failures:
        print(f"  FAIL  {c.name}: model {c.model!r} vs reference {c.reference!r}")

    print("\nCost against feed assay\n" + "-" * 62)
    for row in analysis.assay_curve(mi, [48, 70, 100, 185]):
        print(f"  {row['assay_mgL']:>6,.0f} mg/L   liquor {row['liquor_t_per_kg']:>7,.1f} t/kg"
              f"   production cost {row['production_cost']:>8,.2f}"
              f"   p* {row['pstar']:>8,.2f}")

    stream_checks = balance_rows(r.streams)
    stream_failures = [row for row in stream_checks if row["Status"] != "PASS"]
    invalid_streams = stream_issues(r.streams)
    print(f"\nFlowsheet: {len(r.streams)} live streams; "
          f"{len(stream_checks) - len(stream_failures)} of {len(stream_checks)} balance checks pass.")
    for issue in invalid_streams:
        print(f"  INVALID {issue}")
    if stream_failures or invalid_streams:
        print("Stream checks failed.")
        return 1
    if failures:
        print(f"\n{len(failures)} check(s) FAILED.")
        return 1
    print("\nAll checks passed. Note that this verifies arithmetic and reproduction of "
          "the source workbook.\nIt validates no input: most are labelled PLACEHOLDER "
          "or ESTIMATE and remain unsourced.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
