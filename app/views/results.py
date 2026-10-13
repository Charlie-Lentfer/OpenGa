"""Results summary: two headline numbers, three charts and the caveats."""

import io

import pandas as pd
import streamlit as st

import charts
import lcop
import state
import ui
from openga_v1.config import CAPEX_MODES, ENERGY_MODES, UNIT_OPS, meta

ui.header()
st.title("Results summary")
ui.callout(
    "What this page does",
    "Shows what the scenario you built costs and emits per kilogram of gallium, where the "
    "cost and emissions come from, and how the answer depends on the gallium content of "
    "the liquor.",
    "<strong>Primary outputs:</strong> levelised cost of production (LCOP), carbon "
    "intensity, and three charts.")
ui.how_to(
    ["Build the scenario on steps 1 to 5, or keep the published defaults.",
     "Press **Run model**. Results stay tied to that run until you run again.",
     "Read the two headline numbers, then the charts. Each chart has a *How to read this* "
     "note.",
     "Open **Before quoting these numbers** before you use a result outside this tool.",
     "Download the summary as CSV if you need the numbers elsewhere."],
    notes="If you change an input after running, the results fade and a banner asks you to "
          "run again.")

if not state.has_run():
    ui.empty_state("Press **Run model** to calculate the levelised cost of production and "
                   "carbon intensity. With no edits, the model runs its published defaults.")
    state.run_button("results_empty")
    ui.footer()
    st.stop()

box = state.results_container()
with box:
    mi = state.run_inputs()
    R = state.results()
    B = lcop.bridge(R)
    runs = lcop.policy_runs(mi)
    pkg = R.policy.label or state.package_name()
    cb, f = R.carbon, R.finance
    names = dict(UNIT_OPS)

    if R.warnings:
        with st.expander(f"{len(R.warnings)} model warning(s): read before using these "
                         "results", expanded=True):
            for w in R.warnings:
                st.warning(w)

    c = st.columns(2)
    c[0].markdown(ui.hero(
        "Levelised cost of production", f"A${B['lcop']:,.0f}", "per kg Ga",
        f"{pkg}. The constant real price that returns a {f.real_wacc:.1%} real cost of "
        f"capital after tax over {R.params['LIFE']:g} years."), unsafe_allow_html=True)
    c[1].markdown(ui.hero(
        "Carbon intensity, scope 1 + 2", f"{cb.scope12:,.1f}", "kg CO₂e per kg Ga",
        f"{cb.total:,.1f} kg CO₂e per kg once upstream and embodied emissions are added "
        "on proxy factors."), unsafe_allow_html=True)

    seen, shown, dupes = {}, [], []
    for run in runs:
        v = run["R"].pstar
        match = next((n for n, x in seen.items() if abs(x - v) < 0.5), None)
        if match:
            dupes.append(f"{run['name']} matches {match}")
            continue
        seen[run["name"]] = v
        shown.append((run["name"], v))
    ui.strip([(n, f"A${v:,.0f}/kg") for n, v in shown], "LCOP under each support package")
    ui.strip([("Overall gallium recovery", f"{R.meb.recovery_overall * 100:,.1f}%"),
              ("Liquor treated", f"{R.meb.liquor_t_per_kg:,.1f} t per kg Ga"),
              ("Fixed capital investment", f"A${R.capex.fci_aud / 1e6:,.0f}M")],
             "Plant at a glance")
    if dupes:
        st.caption("Not listed: " + "; ".join(dupes) + ".")

    st.write("")
    left, right = st.columns(2)
    with left:
        ui.chart(charts.stacked_by_unit(
            pd.DataFrame(lcop.by_unit(R, B)),
            ["Capital recovery", "Fixed operating", "Variable operating"],
            "LCOP by unit operation", "A$ / kg Ga", names=names), "lcop_unit",
            f"Columns add to the {pkg.lower()} LCOP. Capital recovery includes company tax "
            "and is net of support. Fixed cost and capital are split by installed-capital "
            "share, an allocation choice rather than a measurement.")
    with right:
        rows = [{"unit": u, "Scope 1": cb.by_up[u]["scope1"], "Scope 2": cb.by_up[u]["scope2"],
                 "Upstream": cb.by_up[u]["upstream"]} for u, _ in UNIT_OPS]
        ui.chart(charts.stacked_by_unit(
            pd.DataFrame(rows), ["Scope 1", "Scope 2", "Upstream"],
            "Carbon by unit operation", "kg CO₂e / kg Ga", names=names), "carbon_unit",
            f"Columns add to {cb.total:,.1f} kg CO₂e per kg. Scope 2 is purchased "
            "electricity. Upstream covers grid losses, gas supply and embodied reagents, "
            "resin, water and waste.")

    curve, dropped = lcop.assay_by_policy(mi, runs)
    cdf = pd.DataFrame(curve)
    series = list(dict.fromkeys(cdf["Policy"]))
    colours = {run["name"]: charts.SERIES4[i % 4] for i, run in enumerate(runs)}
    ui.chart(charts.lines_by_series(
        cdf, "assay_mgL", "LCOP", "Policy", series, [colours[n] for n in series],
        "LCOP against the gallium content of the liquor", "Gallium in Bayer liquor (mg/L)",
        "A$ / kg Ga", marker_x=R.params["GaFeed"],
        marker_label=f"this run: {R.params['GaFeed']:g} mg/L"), "assay",
        "One line per support package. Less gallium in the liquor means more liquor per "
        "kilogram, so cost climbs faster as the assay falls. No Australian refinery has "
        "published an assay, which is why the cost is shown across a range."
        + (f" Not drawn: {'; '.join(dropped)}." if dropped else ""))

    st.write("")
    with st.expander("Before quoting these numbers"):
        b = R.capex
        st.markdown(f"""
- This is a **Class 5** screening estimate (AACE 18R-97, roughly −50% to +100%).
- Capital carries an equipment-list completeness factor of **{b.completeness_factor:g}**.
  The itemised list costs out at **{b.raw_share_of_reference * 100:.0f}%** of the published
  comparable; **{b.completeness_required:.1f}** would reconcile them exactly.
- The LCOP is the minimum price that clears the cost of capital under these assumptions.
  It is not a bankable price, a forecast or a negotiated contract.
- The policy packages are hypothetical. No government has committed to any of them.
- Carbon is a **screening inventory, not a product LCA**. Scope 1 + 2 rests on national
  factors; the rest of the {cb.total:,.1f} kg CO₂e/kg rests on proxy embodied factors.
""")

    with st.expander("Settings and inputs used in this run"):
        cfg = mi.cfg
        st.markdown(ui.esc_dollars(
            f"**Capital cost method:** {CAPEX_MODES[cfg.capex_mode].split(' — ')[0]}  \n"
            f"**Energy model:** {ENERGY_MODES[cfg.energy_mode].split(' — ')[0]}  \n"
            f"**Support package:** {pkg}  \n"
            f"**Run at:** {st.session_state.run['at']}"))
        ov = st.session_state.run["overrides"]
        if ov:
            ui.table(pd.DataFrame([{"Input": meta(k)["label"], "Key": k,
                                    "Default": meta(k).get("default"), "This run": v}
                                   for k, v in sorted(ov.items())]),
                     {"Default": "{:,.6g}", "This run": "{:,.6g}"})
        else:
            st.caption("No inputs changed: this run uses the published defaults.")

    with st.expander("Glossary"):
        st.markdown("""
- **LCOP** · levelised cost of production. The constant real price per kilogram at which
  the project's net present value is zero after company tax.
- **Real WACC** · weighted average cost of capital, net of inflation. The return the plant
  must earn for its lenders and owners.
- **FCI** · fixed capital investment. Installed equipment plus offsites, engineering and
  contingency.
- **CMPTI** · Critical Minerals Production Tax Incentive, a refundable tax offset on
  eligible processing cost.
- **Scope 1 / Scope 2** · emissions from fuel burnt on site / from purchased electricity
  and steam.
- **Upstream** · emissions from making and supplying what the plant buys.
- **4N** · 99.99% pure gallium.
""")

    out = [("LCOP", n, f"{v:.2f}", "A$/kg Ga") for n, v in shown]
    out += [("Carbon", "Scope 1 + 2", f"{cb.scope12:.3f}", "kg CO2e/kg Ga"),
            ("Carbon", "All boundaries", f"{cb.total:.3f}", "kg CO2e/kg Ga"),
            ("Plant", "Overall gallium recovery", f"{R.meb.recovery_overall:.4f}", "fraction"),
            ("Plant", "Liquor treated", f"{R.meb.liquor_t_per_kg:.3f}", "t per kg Ga"),
            ("Plant", "Fixed capital investment", f"{R.capex.fci_aud:.0f}", "A$"),
            ("Finance", "Real WACC", f"{f.real_wacc:.5f}", "fraction")]
    out += [("Input changed", meta(k)["label"], f"{v:.6g}", meta(k)["unit"])
            for k, v in sorted(st.session_state.run["overrides"].items())]
    buf = io.StringIO()
    pd.DataFrame(out, columns=["Section", "Item", "Value", "Unit"]).to_csv(buf, index=False)
    st.download_button("Download summary (CSV)", buf.getvalue(), "openga_results.csv",
                       "text/csv", icon=":material/download:")
ui.footer()
