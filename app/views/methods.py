"""Methods, model checks, evidence status and sources."""

import pandas as pd
import streamlit as st

import state
import ui
from openga_v1 import validation
from openga_v1.config import meta

ui.header()
st.title("Methods, checks and sources")
ui.callout(
    "What this page does",
    "Explains how the main results are calculated, confirms the model's arithmetic and "
    "its agreement with the reference workbook, and lists where every input comes from.",
    "<strong>Primary outputs:</strong> check status, inputs by evidence status, and the "
    "principal sources.")
ui.how_to(
    ["Read **How the LCOP is calculated** if you are new to levelised cost.",
     "Check the status banner. A failed internal check means the model is broken for "
     "these inputs, not merely uncertain.",
     "Open **Inputs by evidence status** to see which inputs are still placeholders.",
     "Cite the principal sources, not this tool, for any input you quote."])

mi = state.run_inputs() if state.has_run() else state.current_inputs()

st.subheader("How the main results are calculated")
with st.expander("How the LCOP is calculated"):
    st.markdown("""
The levelised cost of production is the constant real price per kilogram at which the
project's after-tax net present value is zero at the real WACC. It is solved in closed form
and checked against a separate year-by-year cash flow (Capital and operating cost step,
*Cash-flow check*). It splits into four parts that add back exactly:

| Part | What it is |
|---|---|
| Operating cost | Variable and fixed cost per kilogram |
| Capital recovery | Fixed and working capital, net of salvage, spread over life at the real WACC |
| Company tax | Tax on the return to capital, after the depreciation deduction |
| Government support | Present value of grant, CMPTI and concessional finance, per kilogram (subtracted) |
""".replace("$", "\\$"))
with st.expander("How carbon is calculated"):
    st.markdown("""
Carbon follows the mass and energy balance. Each kilogram of reagent, kWh of electricity and
GJ of gas the balance requires is multiplied by its emission factor and allocated to the unit
operation that uses it. Scope 1 is fuel burnt on site, scope 2 is purchased electricity and
steam, and upstream covers grid losses, fuel supply and embodied reagents, resin, water and
waste. The Bayer liquor enters with no upstream burden.
""")
with st.expander("How cost and carbon are split between unit operations"):
    st.markdown("""
Allocation changes attribution, never totals.
- **Sulfuric acid → UP4**, the acid make-up unit, not UP5 where it is consumed.
- **Resin make-up → UP6**, where the resin is replaced; the initial charge stays capital at UP2.
- **Liquor circuit pumping → UP1/UP2** on `AL_LIQ1`, the one typed allocation share.
- **Secondary pumping → UP3/UP5/UP6** by the volumes each circuit moves.
- **Ancillary power, fixed cost and capital** by installed-capital share. Labour and overhead
  on that basis is an assumption: a real plant staffs to shifts, not to capital.
""")

st.subheader("Model checks")
groups = validation.run_all(mi)
summ = validation.summary(groups)
failed = [ck.name for g in ("internal", "regression") for ck in groups[g]
          if ck.kind != "info" and ck.verdict != "PASS"]
line = (f"Internal consistency {summ['internal']} · workbook regression "
        f"{summ['regression']} · documented divergences {summ['divergence']}")
basis = "your last run" if state.has_run() else "the published defaults"
if failed:
    st.error(f"{len(failed)} check(s) failing on {basis}: {', '.join(failed)}. {line}.")
else:
    st.success(f"All checks pass on {basis}. {line}.")
st.caption("These checks confirm arithmetic, closure and that the Python reproduces the "
           "workbook. **They validate no input.**")
for gname, gtitle, blurb in [
    ("internal", "Internal consistency",
     "Arithmetic and closure. A failure here means the model is broken, not merely "
     "uncertain."),
    ("regression", "Workbook regression",
     "Does the Python still reproduce OpenGa_v3.3_Carbon.xlsx? A failure means the two have "
     "drifted apart."),
    ("divergence", "Documented divergences",
     "Where this model and the published inventory part company. Reported, not failed."),
]:
    with st.expander(f"{gtitle} · {summ[gname]}"):
        st.caption(blurb)
        ui.table(pd.DataFrame([{"Check": ck.name, "Model": ck.model,
                                "Reference": ck.reference, "Deviation": ck.deviation,
                                "Verdict": ck.verdict, "Note": ck.note}
                               for ck in groups[gname]]),
                 {"Model": "{:,.6g}", "Reference": "{:,.6g}", "Deviation": "{:.2e}"})

st.subheader("Evidence and sources")
with st.expander("Inputs by evidence status"):
    stat = {}
    for k in mi.params:
        mm = meta(k)
        if "default" in mm:
            stat.setdefault(mm["status"], []).append(k)
    ui.table(pd.DataFrame([{"Status": s, "Count": len(v),
                            "Keys": ", ".join(sorted(v)[:14]) + ("…" if len(v) > 14 else "")}
                           for s, v in sorted(stat.items(), key=lambda kv: -len(kv[1]))]))
    st.caption("The feed assay, caustic dose, completeness factor, route prices and embodied "
               "factors are the inputs most in need of evidence. Each input's own source "
               "is in its help tooltip on the step pages.")

with st.expander("Principal sources"):
    st.markdown("""
- **Towler & Sinnott**, *Chemical Engineering Design* 2nd ed., Table 7.2 — equipment
  correlations, Hand factors, location factor, OSBL, engineering and contingency.
- **DCCEEW**, *Australian National Greenhouse Accounts Factors 2025* — WA SWIS scope 2 and
  scope 3, natural gas combustion and state upstream factors.
- **CSIRO**, *GenCost 2025-26* — battery capital, NEM generation price band.
- **IEEFA** (Nov 2025) — Western Australian domestic gas prices.
- **Energies** 2025, 18(24):6413 — utility PV and onshore wind life-cycle intensities.
- **GJETA** 2025 — lithium-ion round-trip efficiency, cycle life, manufacturing emissions.
- **Lu et al. 2026**, *Solar Energy* 303 — onsite PV+BESS and Australian industrial tariffs.
- **Luo et al. 2025**, *Int. J. Life Cycle Assess.* 30:1545–1559 — the only
  industrial-scale primary gallium LCA (see the divergence table for its Table 2 exponent defect).
- **Zhao et al. 2016**, *ACS Sust. Chem. Eng.*; **Gorzin et al.**; **Materials** 2024,
  17(16), 4109 — resin performance.
- **Wesselkaemper et al. 2025**; **Alcoa** Wagerup disclosures — capital comparables.
""")
ui.footer()
