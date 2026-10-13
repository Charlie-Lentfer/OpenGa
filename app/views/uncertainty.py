"""Uncertainty: one-at-a-time sensitivity and Monte Carlo on the Run snapshot."""

import pandas as pd
import streamlit as st

import charts
import state
import ui
from openga_v1 import analysis

ui.header()
st.title("Uncertainty")
ui.callout(
    "What this page does",
    "Shows which inputs move the answer most and how wide the plausible range is. The "
    "tornado changes one input at a time between a sourced low and high. Monte Carlo "
    "draws all uncertain inputs together and runs the full model on every draw.",
    "<strong>Primary outputs:</strong> ranked input swings, and P10, P50 and P90 for the "
    "LCOP or carbon intensity.")
ui.how_to(
    ["Run the model first. Both analyses start from the scenario in your last run.",
     "Choose the result to test: LCOP or carbon intensity.",
     "Read the tornado from the top. The longest bars are where better evidence would "
     "narrow the answer most.",
     "Set the number of Monte Carlo trials and press **Run Monte Carlo**. 1,000 trials "
     "takes about a second.",
     "Read P10 to P90 as the range, not the single most likely value."],
    notes="The ranges and distributions, with their sources, are listed under each chart.")

if not state.has_run():
    ui.empty_state("Press **Run model** first. The sensitivity analysis starts from the "
                   "scenario in your last run.")
    state.run_button("unc_empty")
    ui.footer()
    st.stop()

box = state.results_container()
with box:
    mi = state.run_inputs()
    R = state.results()
    pkg = state.package_name()
    target = st.radio("Result to test", ["pstar", "carbon"], horizontal=True, key="unc_target",
                      format_func=lambda t: {"pstar": f"LCOP ({pkg})",
                                             "carbon": "Carbon intensity, all boundaries"}[t])
    base_v = {"pstar": R.pstar, "carbon": R.carbon.total}[target]
    unit = "kg CO₂e / kg Ga" if target == "carbon" else "A$ / kg Ga"
    base_txt = (f"A${base_v:,.0f}/kg" if target == "pstar" else f"{base_v:,.1f} kg CO₂e/kg")

    st.markdown("#### Which inputs matter most")
    tor = analysis.tornado(mi, target=target)
    ui.chart(charts.tornado(tor, base_v, f"Change from this run ({base_txt})",
                            f"Change in {unit}"), "tornado",
             "Each bar is one input moved from its low to its high value with everything "
             "else held. Bars are sorted by total swing.")
    if mi.cfg.resin_preset != state.CUSTOM_RESIN:
        st.caption("Ion exchange recovery shows no swing because the selected resin preset "
                   "fixes it. Choose the Custom preset on step 2 to vary it.")
    with st.expander("Ranges and their sources"):
        ui.table(pd.DataFrame(tor)[["label", "low_input", "high_input", "low", "high", "swing",
                                    "basis"]].rename(columns={
                                        "label": "Input", "low_input": "Low input",
                                        "high_input": "High input", "low": "Result at low",
                                        "high": "Result at high", "swing": "Swing",
                                        "basis": "Basis"}),
                 {"Low input": "{:,.4g}", "High input": "{:,.4g}", "Result at low": "{:,.1f}",
                  "Result at high": "{:,.1f}", "Swing": "{:,.1f}"})

    st.markdown("#### How wide is the range")
    c = st.columns([2, 2, 1], vertical_alignment="bottom")
    trials = c[0].select_slider("Trials", [200, 500, 1000, 2000, 5000], value=1000,
                                key="mc_trials")
    seed = c[1].number_input("Random seed", value=20260909, step=1, key="mc_seed",
                             help="Keep the seed to reproduce a result exactly.")
    go = c[2].button("Run Monte Carlo", type="primary", key="mc_go", width="stretch")
    if go:
        with st.spinner(f"Running {trials:,} trials…"):
            st.session_state.mc = analysis.monte_carlo(mi, trials=int(trials), seed=int(seed))
    mc = st.session_state.get("mc")
    if mc is None:
        st.caption("Press **Run Monte Carlo** to sample. The full model runs on every draw.")
    else:
        vals, s = mc[target], mc["stats"][target]
        ui.strip([("P10", f"{s['p10']:,.0f} {unit}"), ("P50", f"{s['p50']:,.0f} {unit}"),
                  ("P90", f"{s['p90']:,.0f} {unit}")],
                 f"Distribution over {mc['trials']:,} trials")
        ui.chart(charts.histogram(analysis.histogram(vals, 20),
                                  f"{'LCOP' if target == 'pstar' else 'Carbon intensity'}"
                                  f" over {mc['trials']:,} trials", unit,
                                  markers={"P10": s["p10"], "P50": s["p50"], "P90": s["p90"]}),
                 "histogram",
                 "Read the tail, not the peak. Assay, recovery and the completeness factor "
                 "all cut one way, so the distribution is skewed to the right.")
        with st.expander("Distributions used"):
            ui.table(pd.DataFrame([{"Input": d.label, "Low": d.low, "Mode": d.mode,
                                    "High": d.high, "Basis": d.basis} for d in mc["specs"]]),
                     {"Low": "{:,.4g}", "Mode": "{:,.4g}", "High": "{:,.4g}"})
            st.caption("Triangular: for most of these, a plausible range and a most likely "
                       "value are all anyone can defend."
                       + (" Ion exchange recovery is drawn but has no effect while a named "
                          "resin preset is selected." if mi.cfg.resin_preset != 4 else ""))
ui.footer()
