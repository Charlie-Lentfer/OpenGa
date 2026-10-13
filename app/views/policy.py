"""Step 5: cost of capital and the government support packages."""

import pandas as pd
import streamlit as st

import charts
import lcop
import state
import ui
from openga_v1 import config, policy as policy_mod

ui.step_intro(
    "5. Finance and policy support",
    "Sets the cost of capital and the government support the plant could receive: a "
    "capital grant, concessional debt and the Critical Minerals Production Tax Incentive "
    "(CMPTI). Support changes the financing, never the plant: every package runs on the "
    "same capital and operating cost.",
    "the LCOP under each support package and what each form of support is worth per "
    "kilogram.")

ui.how_to(
    ["Keep the **v3.1 policy model** unless you are reproducing the legacy WP4 workbook.",
     "Choose the **package the Results summary leads with**. The others are listed beside it.",
     "Review tax, the CAPM cost-of-capital build-up and the concessional debt terms.",
     "Set CMPTI and capital grant terms if you are testing a specific policy design. "
     "They apply to every package that includes that form of support.",
     "Press **Run model** to compare packages."],
    ["LCOP under every package and the saving against no support.",
     "Each package's saving split into capital grant, concessional finance and CMPTI.",
     "The WACC build-up, CMPTI eligibility register and loan schedule."],
    "The packages are hypothetical. No government has committed to them, Export Finance "
    "Australia publishes no universal concessional rate, and the grant's tax treatment "
    "would need a ruling. The **Custom** package has no editor in this version, so it "
    "returns the same result as no support.")

st.subheader("Method choices")
c = st.columns(2)
with c[0]:
    state.policy_model_select()
with c[1]:
    state.package_select()

st.subheader("Inputs")
state.input_sections([("Finance", "Tax, inflation and salvage"),
                      ("Finance", "Cost of capital"),
                      ("Finance", "Concessional debt"),
                      ("Policy", "CMPTI"),
                      ("Policy", "Capital grant"),
                      ("Policy", "Offtake assessment")])
state.run_footer("policy")

st.subheader("Policy results")
box = state.results_container()
if box is None:
    ui.empty_state("Press **Run model** to compare the support packages.")
else:
    with box:
        mi = state.run_inputs()
        R = state.results()
        runs = lcop.policy_runs(mi)
        pol = R.policy
        if mi.cfg.policy_model == "v31":
            ref = runs[0]["R"].pstar
            rows, seen, dupes = [], {}, []
            for run in runs:
                match = next((n for n, x in seen.items()
                              if abs(x - run["R"].pstar) < 0.5), None)
                if match:
                    dupes.append(f"{run['name']} matches {match}")
                    continue
                seen[run["name"]] = run["R"].pstar
                b = lcop.bridge(run["R"])
                rows.append({"Package": run["name"], "LCOP": b["lcop"],
                             "Saving vs no support": ref - b["lcop"],
                             "Capital grant": b["grant"],
                             "Concessional finance": b["concession"],
                             "CMPTI": b["cmpti"], "Real WACC": run["R"].finance.real_wacc})
            pdf = pd.DataFrame(rows)
            left, right = st.columns([3, 2])
            with left:
                ui.chart(charts.stacked_hbar(
                    pdf, "Package", ["Capital grant", "Concessional finance", "CMPTI"],
                    "What each package is worth", "Reduction in LCOP, A$ / kg Ga"),
                    "packages",
                    "Bar length is the LCOP saving against no support, split by where it "
                    "comes from.")
            with right:
                ui.table(pdf[["Package", "LCOP", "Saving vs no support"]],
                         {"LCOP": "{:,.0f}", "Saving vs no support": "{:,.0f}"})
                st.caption("A$ per kg Ga." + (f" Not listed: {'; '.join(dupes)}."
                                              if dupes else ""))

            with st.expander("Package detail"):
                ui.table(pdf, {"LCOP": "{:,.2f}", "Saving vs no support": "{:,.2f}",
                               "Capital grant": "{:,.2f}", "Concessional finance": "{:,.2f}",
                               "CMPTI": "{:,.2f}", "Real WACC": "{:.2%}"})
                for k in config.default_policy_packages(mi.resolved()):
                    st.caption(f"**{k.name}.** {k.note}" if getattr(k, "note", None)
                               else k.name)

            with st.expander("Cost of capital build-up"):
                fb = pol.financing
                ui.table(pd.DataFrame([
                    {"Item": "Debt / equity", "Value": fb.debt_equity},
                    {"Item": "Levered beta (Hamada)", "Value": fb.beta_levered},
                    {"Item": "Cost of equity (nominal, CAPM)", "Value": fb.ke},
                    {"Item": "Commercial cost of debt (nominal)", "Value": fb.kd_commercial},
                    {"Item": "Blended cost of debt (nominal)", "Value": fb.kd_blended},
                    {"Item": "Cost of debt used in WACC", "Value": fb.kd_in_wacc},
                    {"Item": "WACC, nominal", "Value": fb.wacc_nominal},
                    {"Item": "WACC, real", "Value": fb.wacc_real},
                ]), {"Value": "{:,.4f}"})
                st.caption("The WACC keeps the commercial debt rate; the concession is valued "
                           "separately over its actual tenor so the benefit is not counted "
                           "twice.")

            with st.expander("CMPTI eligibility register"):
                ui.table(pd.DataFrame(policy_mod.eligibility_register(R.opex.variable,
                                                                      R.opex.fixed)),
                         {"cost": "{:,.0f}", "fraction": "{:.0%}", "eligible": "{:,.0f}"})
                st.caption("The fractions are what this register asserts, not what the ATO "
                           "has confirmed for a gallium flowsheet.")

            if pol.concession_schedule:
                with st.expander(f"Concessional finance schedule · {state.package_name()}"):
                    cs = pd.DataFrame(pol.concession_schedule)
                    st.altair_chart(charts.simple_bar(
                        cs.assign(Year=cs["year"].astype(str))[["Year", "saving"]].rename(
                            columns={"saving": "After-tax interest saving"}),
                        "Year", "After-tax interest saving",
                        "After-tax interest saving over the loan tenor", "Year", "A$",
                        horizontal=False, fmt=",.0f"), width="stretch")
                    st.caption("Zero after the tenor expires: a concessional loan runs for "
                               "its term, not the life of the plant.")
        else:
            st.markdown("#### Legacy WP4 scenarios")
            ui.table(pd.DataFrame([{"Scenario": run["name"], "LCOP": run["R"].pstar,
                                    "OPEX offset": run["R"].policy.value.opex_offset,
                                    "Real WACC": run["R"].policy.value.real_wacc,
                                    "Price floor (A$/kg)": run["R"].policy.value.price_floor}
                                   for run in runs]),
                     {"LCOP": "{:,.0f}", "OPEX offset": "{:.0%}", "Real WACC": "{:.2%}",
                      "Price floor (A$/kg)": "{:,.0f}"})

        if pol.notes:
            with st.expander("Notes on the selected package"):
                for n in pol.notes:
                    st.caption(f"→ {n}")
ui.footer()
