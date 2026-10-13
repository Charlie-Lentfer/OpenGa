"""Step 1: plant size and the liquor it treats."""

import streamlit as st

import state
import ui

ui.step_intro(
    "1. Feed liquor and plant basis",
    "Sets how much gallium the plant makes and what is in the liquor it treats. The gallium "
    "assay drives liquor flow, and liquor flow sizes most of the plant. No Australian "
    "refinery has published an assay, so the default is a survey midpoint.",
    "liquor flow the plant must process, tonnes of liquor per kilogram of gallium, and "
    "gallium fed per kilogram produced.")

ui.how_to(
    ["Keep the 100 t/yr capacity unless you are testing scale.",
     "Set the gallium in spent Bayer liquor (mg/L) you want to test. It is the most "
     "influential input in the model.",
     "Leave the rest of the liquor chemistry at its defaults unless you have refinery data.",
     "Press **Run model** and check the liquor figures at the foot of this page."],
    ["Liquor flow in m³/h and in tonnes per kilogram of gallium.",
     "Gallium fed to the plant per kilogram of product."],
    "To see cost across a range of assays rather than one value, use the assay chart on "
    "the Results summary.")

st.subheader("Inputs")
state.input_sections([("Plant basis", "Capacity, hours and life"),
                      ("Plant basis", "Feed liquor chemistry")])
state.run_footer("feed")

st.subheader("What these inputs produce")
box = state.results_container()
if box is None:
    ui.empty_state()
else:
    with box:
        m = state.results().meb
        c = st.columns(3)
        c[0].metric("Liquor flow (m³/h)", f"{m.liquor_m3_h:,.0f}")
        c[1].metric("Liquor per kg of gallium (t)", f"{m.liquor_t_per_kg:,.1f}")
        c[2].metric("Gallium fed per kg produced (kg)", f"{m.feed_ga_kg:,.2f}",
                    help="The inverse of overall recovery. Set by the recovery cascade "
                         "on step 2.")
ui.footer()
