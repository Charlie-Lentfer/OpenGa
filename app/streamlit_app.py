"""
OpenGa - interim Streamlit interface (WP4 section J).

DISPOSABLE sanity-check UI wrapping the openga backend.  No styling investment:
this exists to exercise openga/ interactively, not as a deliverable.  It will
be replaced by Rasmeet's OpenCu-derived layout (section K) with widgets
re-pointed at the same openga functions -- no backend change required.

Run:  streamlit run app/streamlit_app.py
"""
from __future__ import annotations

import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dataclasses import replace

import pandas as pd
import streamlit as st

from openga import meb, carbon, upcost, finance, policy, validation, sensitivity, montecarlo
from openga.config import DEFAULT, PRICE_LADDER_USD

st.set_page_config(page_title="OpenGa (interim)", layout="wide")
st.title("OpenGa - gallium recovery techno-economic model (interim UI)")
st.caption("Source of truth: WP3_Balance_v3_3.xlsx + Ga_Financial_Model_WP4_v2.xlsx. "
           "All EFs and many prices are PLACEHOLDERS.")

# ---- sidebar: a few live inputs feeding the config -------------------------
with st.sidebar:
    st.header("Inputs")
    feed = st.slider("Feed Ga (mg/L)", 50, 250, int(DEFAULT.meb.ga_feed))
    elec_price = st.slider("Electricity ($/MWh)", 80, 250, int(DEFAULT.prices.electricity.base))
    naoh_price = st.slider("NaOH ($/t)", 400, 1200, int(DEFAULT.prices.naoh.base))
    resin_price = st.slider("IX resin ($/kg)", 5, 30, int(DEFAULT.prices.resin.base))
    pol = st.selectbox("Policy scenario", [1, 2, 3],
                       format_func=lambda s: policy.scenario(s).name)

cfg = DEFAULT.with_(meb=replace(DEFAULT.meb, ga_feed=float(feed)))
cfg = cfg.with_(prices=replace(cfg.prices,
                               electricity=replace(cfg.prices.electricity, base=float(elec_price)),
                               naoh=replace(cfg.prices.naoh, base=float(naoh_price)),
                               resin=replace(cfg.prices.resin, base=float(resin_price))))
res = meb.run(cfg)

tabs = st.tabs(["Process & MEB", "Cost per UP", "Carbon", "Financials & MVP",
                "Price Ladder", "Break-even", "Sensitivity / Monte Carlo",
                "Policy Scenarios", "Validation"])

with tabs[0]:
    st.subheader("Mass & energy balance (per kg 4N Ga)")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Throughput", f"{res.throughput_t:.3f} t/kg")
    c2.metric("Electricity", f"{res.electricity_kwh:.2f} kWh/kg")
    c3.metric("Overall recovery", f"{res.overall_recovery*100:.2f}%")
    c4.metric("Master check", f"{res.master_check:.1e}")
    df = pd.DataFrame(res.per_up, index=meb.UP_NAMES).fillna(0.0)
    st.dataframe(df, use_container_width=True)

with tabs[1]:
    st.subheader("Variable OPEX per unit operation (AUD/kg)")
    u = upcost.run(cfg, res)
    st.dataframe(pd.DataFrame([{"Unit op": x.name, **x.lines, "Total": x.total}
                               for x in u.per_up]).fillna(0.0), use_container_width=True)
    st.metric("Variable OPEX total", f"{u.variable_total_per_kg:.2f} AUD/kg")

with tabs[2]:
    st.subheader("Carbon (kg CO2e/kg Ga) - PLACEHOLDER emission factors")
    cr = carbon.run(cfg, res)
    st.dataframe(pd.DataFrame([{"Unit op": e.name, "Scope 2": e.scope2_electricity,
                               "Scope 1": e.scope1_steam, "Embodied": e.embodied,
                               "S1+S2": e.s1_s2, "Total": e.total} for e in cr.per_up]),
                 use_container_width=True)
    c1, c2 = st.columns(2)
    c1.metric("S1 + S2", f"{cr.s1_s2_total:.2f}")
    c2.metric("+ embodied", f"{cr.total_with_embodied:.2f}")

with tabs[3]:
    st.subheader("Financials")
    fr = finance.run(cfg, policy.scenario(pol), res)
    c1, c2, c3 = st.columns(3)
    c1.metric("MVP p*", f"{fr.mvp:,.2f} AUD/kg")
    c2.metric("Pre-tax LCOP", f"{fr.lcop_pretax:,.2f} AUD/kg")
    c3.metric("FCI", f"{fr.fci/1e6:,.1f} AUD M")
    st.bar_chart(pd.Series(fr.cost_stack, name="AUD/kg"))

with tabs[4]:
    st.subheader("MVP vs WP1 price ladder (AUD/kg)")
    fr = finance.run(cfg, policy.scenario(pol), res)
    ladder = {k: v * cfg.norm.fx_usd_aud for k, v in PRICE_LADDER_USD.items()}
    ladder["OpenGa MVP p*"] = fr.mvp
    st.bar_chart(pd.Series(ladder, name="AUD/kg"))
    st.caption("Ladder benchmarks are PLACEHOLDERS pending WP1 consolidated price table.")

with tabs[5]:
    st.subheader("Break-even feed concentration")
    pts = sensitivity.breakeven_feed(cfg)
    df = pd.DataFrame([{"Feed mg/L": p.feed_mg_l, "MVP AUD/kg": p.mvp} for p in pts]).set_index("Feed mg/L")
    st.line_chart(df)
    st.caption("LIMITATION: capital NOT rescaled -> low-concentration MVPs optimistic.")

with tabs[6]:
    st.subheader("Sensitivity (tornado)")
    bars = sensitivity.tornado(cfg)
    st.dataframe(pd.DataFrame([{"Variable": b.variable, "Low p*": b.low_mvp,
                               "High p*": b.high_mvp, "Swing": b.swing} for b in bars]),
                 use_container_width=True)
    if st.button("Run Monte Carlo (500 trials)"):
        mc = montecarlo.run(cfg, trials=500)
        st.write(mc.summary())
        st.bar_chart(pd.Series(mc.samples).value_counts(bins=30).sort_index())

with tabs[7]:
    st.subheader("Policy scenarios")
    rows = []
    for s in (1, 2, 3):
        pr = policy.run(s, cfg, res)
        rows.append({"#": s, "Scenario": pr.scenario.name, "OPEX offset": pr.scenario.opex_offset,
                     "WACC case": pr.scenario.wacc_case, "Price floor": pr.scenario.price_floor,
                     "MVP p*": pr.mvp})
    st.dataframe(pd.DataFrame(rows), use_container_width=True)
    st.info(policy.price_floor_status())
    st.success(f"Baseline neutrality check: deviation = {policy.assert_baseline_neutral(cfg):.1e}")

with tabs[8]:
    st.subheader("Wesselkaemper et al. 2025 replication (2024 USD)")
    w = validation.wesselkaemper(cfg)
    st.dataframe(pd.DataFrame([{"Test": t.name, "Engine": t.engine, "Target": t.target,
                               "Deviation %": t.deviation*100, "Tolerance %": t.tolerance*100,
                               "Status": t.status} for t in w.tests]), use_container_width=True)
    st.metric("All tests pass", "YES" if w.all_pass() else "NO")
