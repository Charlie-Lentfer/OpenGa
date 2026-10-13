"""Step 3: capital cost method, equipment, capital factors and operating cost."""

import pandas as pd
import streamlit as st

import charts
import lcop
import state
import ui
from openga_v1.config import CAPEX_MODES, UNIT_OPS

ui.step_intro(
    "3. Capital and operating cost",
    "Turns the flowsheet into money. Equipment is sized from the mass balance and costed "
    "from published correlations, then built up to fixed capital. Operating cost adds "
    "reagents, utilities, labour and maintenance.",
    "fixed capital investment, annual operating cost, and how the levelised cost of "
    "production is built from them.")

ui.how_to(
    ["Choose a **capital cost method**. Bottom-up is the default; six-tenths scaling, your "
     "own total, or one installed cost per unit operation are alternatives.",
     "If you choose your own total or per-stage costs, enter them in the boxes that appear.",
     "Check the escalation, location and currency settings. They carry 2010 US Gulf Coast "
     "correlations to current Australian dollars.",
     "Review unit prices for electricity, reagents and resin, and the fixed-cost "
     "allowances.",
     "Press **Run model** to see the cost build-up."],
    ["A bridge from operating cost to the LCOP, with each part explained.",
     "Capital build-up, equipment list, operating cost lines, LCOP by unit operation and "
     "a cash-flow check, each in its own panel."],
    "The capital estimate carries an equipment-list completeness factor. Read *Before "
    "quoting these numbers* on the Results summary.")

st.subheader("Method choices")
state.capex_select()
state.capex_entries()

st.subheader("Inputs")
state.input_sections([("Equipment", "Sizing parameters"),
                      ("Equipment", "Costing allowances"),
                      ("Capital", "Escalation, location and currency"),
                      ("Capital", "Installation and factorial build-up"),
                      ("Capital", "Comparable plant (six-tenths mode)"),
                      ("Operating cost", "Unit prices"),
                      ("Operating cost", "Fixed cost")])
state.run_footer("cost")

st.subheader("Cost results")
box = state.results_container()
if box is None:
    ui.empty_state("Press **Run model** to see the capital estimate and how the LCOP is "
                   "built.")
else:
    with box:
        R = state.results()
        B = lcop.bridge(R)
        pkg = state.package_name()
        keep = 1.0 - R.policy.value.opex_offset
        f = R.finance

        c = st.columns(2)
        c[0].metric("Fixed capital investment", f"A${R.capex.fci_aud / 1e6:,.0f}M")
        c[1].metric("Operating cost per year", f"A${R.opex.total * keep / 1e6:,.1f}M")

        # Every support package on the same plant, de-duplicated (Custom has no
        # editor and returns the no-support result).
        runs = lcop.policy_runs(state.run_inputs())
        colours = {r["name"]: charts.SERIES4[i % 4] for i, r in enumerate(runs)}
        sel = next((r for r in runs if r["name"] == pkg), runs[0])
        kept, dupes = [], []
        for r in runs:
            if r is not sel and any(abs(r["R"].pstar - k["R"].pstar) < 0.5
                                    for k in kept + [sel]):
                dupes.append(r["name"])
                continue
            kept.append(r)
        bridges = {r["name"]: lcop.bridge(r["R"]) for r in kept}
        any_support = any(b["support"] > 0.005 for b in bridges.values())
        packages = []
        for r in kept:
            b = bridges[r["name"]]
            steps = [{"label": "Operating cost", "value": b["operating"], "kind": "add"},
                     {"label": "Capital recovery", "value": b["capital"], "kind": "add"},
                     {"label": "Company tax", "value": b["tax"], "kind": "add"}]
            if any_support:
                steps.append({"label": "Government support", "value": -b["support"],
                              "kind": "subtract"})
            steps.append({"label": "LCOP", "value": b["lcop"], "kind": "total"})
            packages.append({"name": r["name"], "steps": steps})

        left, right = st.columns([3, 2])
        with left:
            ui.chart(charts.bridge_compare(
                packages, sel["name"], colours, "How the LCOP is built",
                f"Solid: {sel['name']} (selected on step 5) · dashed: the other packages",
                "A$ / kg Ga"), "bridge",
                f"Each bar starts where the one before it ends, and the last group is the "
                f"LCOP. Solid bars are **{sel['name']}**; dashed outlines are the other "
                "packages on the same plant, labelled where they differ. Change the selected "
                "package on step 5."
                + (f" Not drawn: {', '.join(dupes)} (same result as another package)."
                   if dupes else ""))
        with right:
            lines = [
                f"**Operating cost · {state.fmt_aud(B['operating'])}/kg**  \nReagents, "
                "electricity, labour, maintenance, insurance and overheads for one kilogram.",
                f"**Capital recovery · {state.fmt_aud(B['capital'])}/kg**  \nRepays fixed "
                f"and working capital at a {f.real_wacc:.2%} real WACC over "
                f"{R.params['LIFE']:g} years.",
                f"**Company tax · {state.fmt_aud(B['tax'])}/kg**  \n{R.params['TAXR']:.0%} "
                "tax on that return, after the depreciation deduction.",
            ]
            if B["support"] > 0.005:
                lines.append(f"**Government support · −{state.fmt_aud(B['support'])}/kg**  \n"
                             f"Capital grant {state.fmt_aud(B['grant'])}, concessional "
                             f"finance {state.fmt_aud(B['concession'])} and CMPTI "
                             f"{state.fmt_aud(B['cmpti'])}, each per kg.")
            st.markdown(ui.esc_dollars("\n\n".join(lines)))
            if abs(B["residual"]) > 0.01:
                st.warning(f"The parts differ from the LCOP by A${B['residual']:,.2f}/kg "
                           "(a legacy price floor is active).")

        cx = R.capex
        with st.expander("Capital cost build-up"):
            st.caption(CAPEX_MODES[state.run_inputs().cfg.capex_mode])
            ui.table(pd.DataFrame([
                {"Item": "ISBL from the correlated equipment list", "A$": cx.isbl_correlated_aud},
                {"Item": "Directly priced items (resin charge, rectifier)",
                 "A$": cx.isbl_direct_aud},
                {"Item": "ISBL, raw bottom-up", "A$": cx.isbl_raw_aud},
                {"Item": f"ISBL applied (completeness factor {cx.completeness_factor:g})",
                 "A$": cx.isbl_aud},
                {"Item": "OSBL (offsites and utilities)", "A$": cx.osbl_aud},
                {"Item": "Engineering and project management", "A$": cx.engineering_aud},
                {"Item": "Contingency", "A$": cx.contingency_aud},
                {"Item": "Fixed capital investment", "A$": cx.fci_aud},
                {"Item": "Working capital", "A$": cx.working_capital_aud},
                {"Item": "Total capital investment", "A$": cx.tci_aud},
            ]), {"A$": "{:,.0f}"})
            st.markdown("**Does the capital number stand up?**")
            c = st.columns(4)
            c[0].metric("Raw bottom-up FCI", f"A${cx.fci_raw_aud / 1e6:,.0f}M")
            c[1].metric("Comparable-plant FCI", f"A${cx.fci_reference_aud / 1e6:,.0f}M")
            c[2].metric("Raw as share of comparable", f"{cx.raw_share_of_reference * 100:,.0f}%")
            c[3].metric("Capital intensity", f"US${cx.intensity_usd_k_per_t:,.0f}k per t/yr")
            for n in cx.notes:
                st.caption(f"→ {n}")

        with st.expander("Equipment list"):
            if R.equipment.out_of_range:
                st.warning(f"{R.equipment.out_of_range} item(s) are sized outside their "
                           "correlation's published range.")
            ui.table(pd.DataFrame([{
                "ID": i.id, "Item": i.name, "UP": i.unit_op, "N": i.n_duty,
                "Size each": i.s_each, "Unit": i.s_unit, "In range?": i.in_range,
                "Installed (2010 US$)": i.installed_usd2010, "Sizing basis": i.basis}
                for i in R.equipment.items]),
                {"N": "{:.0f}", "Size each": "{:,.4g}", "Installed (2010 US$)": "{:,.0f}"})
            st.caption("Towler & Sinnott, Chemical Engineering Design 2nd ed., Table 7.2. "
                       "US Gulf Coast basis, January 2010, CEPCI 532.9.")

        with st.expander("Operating cost lines"):
            ox, Q = R.opex, R.params["CapProd"]
            if R.energy.use_mix:
                st.info(f"The blended electricity price of A${R.energy.mix_price:,.2f}/MWh "
                        "is feeding operating cost.")
            ui.table(pd.DataFrame(
                [{"Line": k, "Type": "Variable", "Quantity": ox.quantities[k][0],
                  "Unit": ox.quantities[k][1], "A$/yr": v, "A$/kg Ga": v / Q}
                 for k, v in ox.variable.items()] +
                [{"Line": k, "Type": "Fixed", "Quantity": None, "Unit": "", "A$/yr": v,
                  "A$/kg Ga": v / Q} for k, v in ox.fixed.items()]),
                {"Quantity": "{:,.1f}", "A$/yr": "{:,.0f}", "A$/kg Ga": "{:,.2f}"})
            if R.policy.value.opex_offset:
                st.caption(f"Legacy OPEX offset of {R.policy.value.opex_offset:.0%} applies "
                           "on top of these gross figures.")

        with st.expander("LCOP by unit operation"):
            ur = pd.DataFrame(lcop.by_unit(R, B))
            ur["Operation"] = [nm for _, nm in UNIT_OPS]
            ur["LCOP"] = ur[["Variable operating", "Fixed operating",
                             "Capital recovery"]].sum(axis=1)
            ur["Share"] = ur["LCOP"] / B["lcop"] if B["lcop"] else 0.0
            ui.table(ur.rename(columns={"unit": "Unit"})[
                ["Unit", "Operation", "Variable operating", "Fixed operating",
                 "Capital recovery", "LCOP", "Share"]],
                {"Variable operating": "{:,.2f}", "Fixed operating": "{:,.2f}",
                 "Capital recovery": "{:,.2f}", "LCOP": "{:,.2f}", "Share": "{:.1%}"})
            st.caption("Allocation changes attribution, never totals. The allocation rules are "
                       "listed on Methods, checks and sources.")
            st.caption(f"Worst allocation residual across all resources: "
                       f"{R.allocation.max_residual:.1e}.")

        with st.expander("Cash-flow check"):
            st.caption(f"The {int(R.params['LIFE']) + 1}-year real cash flow is built "
                       "separately from the closed-form LCOP and priced at it. Its NPV "
                       "should be zero.")
            st.metric("NPV at the LCOP", f"A${f.npv_at_pstar:,.2f}")
            cf = pd.DataFrame(f.cash_flow)
            ui.table(cf, {c: "{:,.0f}" for c in cf.columns if c not in ("year", "discount")}
                     | {"discount": "{:.4f}"}, height=320)
            st.caption("Real, constant 2026 AUD. Nominal historical-cost tax depreciation is "
                       "deflated before discounting, so the real cash flow is not credited "
                       "with a nominal tax shield.")
ui.footer()
