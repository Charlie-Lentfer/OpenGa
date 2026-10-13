"""Landing page: what the model is, how to use it and who built it."""

import streamlit as st

import ui

ui.header()
st.markdown("<span class='ga-chip'>OPENGA V2</span>"
            "<span class='ga-chip'>GALLIUM FROM BAYER LIQUOR</span>"
            "<span class='ga-chip'>COST + CARBON</span>", unsafe_allow_html=True)
st.title("Gallium Recovery Cost and Emissions Assessment")
st.markdown("<p class='ga-kicker'>An open techno-economic and carbon model for recovering "
            "4N gallium from a slipstream of spent Bayer liquor at an Australian alumina "
            "refinery.</p>", unsafe_allow_html=True)

ui.callout(
    "Start here",
    "Work through the five <b>Build the scenario</b> steps in the sidebar. Every input "
    "starts at a published or documented default, so change only what you have evidence "
    "for. Then press <b>Run model</b>. The <b>Results summary</b> shows the levelised cost "
    "of production and the carbon intensity per kilogram of gallium.",
    "Nothing is calculated until you press Run, and results stay tied to that run until "
    "you run again.")

st.subheader("How the model is built")
st.caption("Eleven unit operations, one mass and energy balance, one cost and carbon basis.")
ui.flow(
    [("Liquor clarification", "UP1",
      "A filter press clears solids from the liquor slipstream. Liquor volume sizes the plant."),
     ("Ion exchange circuit", "UP2–UP6",
      "Resin loads gallium and the liquor returns to the refinery. Wash, elution and "
      "regeneration follow."),
     ("Precipitation and purification", "UP7–UP9",
      "Gallium is precipitated from the eluate, centrifuged and purified."),
     ("Electrowinning and refining", "UP10–UP11",
      "Gallium is plated from the electrolyte and refined to 4N (99.99%).")],
    ("LCOP and carbon",
     "A$ and kg CO₂e per kg of gallium, under each support package."))

st.subheader("Questions this tool answers")
ui.cards([
    ("What price would the plant need?",
     "The levelised cost of production (LCOP): the constant real price per kilogram at "
     "which the plant just earns its cost of capital after company tax."),
    ("Where does the cost come from?",
     "Operating cost, capital recovery and tax, and how they split across the eleven "
     "unit operations."),
    ("How much does government support help?",
     "Capital grants, concessional finance and the Critical Minerals Production Tax "
     "Incentive, compared package by package."),
    ("How carbon-intensive is it?",
     "Scope 1, scope 2 and upstream emissions per kilogram, and what a different "
     "electricity supply would change."),
    ("Which inputs matter most?",
     "A tornado chart and Monte Carlo simulation over the uncertain inputs, led by the "
     "gallium content of the liquor."),
])

with st.expander("Model scope and units"):
    st.markdown("""
- **Product:** 4N gallium metal. **Basis:** 100 t/yr, the design capacity Alcoa has
  announced for its Wagerup gallium project.
- **Feed:** spent Bayer liquor, returned to the refinery after gallium is removed. The
  liquor carries no upstream emissions burden (cut-off allocation).
- **Money:** real Australian dollars, constant 2026 basis. Equipment costs start from
  Towler & Sinnott correlations (US Gulf Coast, 2010) and are escalated and localised.
- **Cost:** levelised cost of production (LCOP) in A$ per kg Ga, after company tax.
- **Carbon:** kg CO₂e per kg Ga. Scope 1 + 2 rests on Australian national factors; the
  upstream share rests on proxy factors.
- **Accuracy:** AACE Class 5 screening estimate, roughly −50% to +100%.
""")

with st.expander("Recommended workflow"):
    st.markdown("""
1. **Feed liquor and plant basis.** Set capacity and the gallium assay you want to test.
2. **Gallium recovery process.** Choose a resin preset and review unit recoveries.
3. **Capital and operating cost.** Choose a capital cost method and check unit prices.
4. **Energy and carbon.** Set the electricity supply mix and emission factors.
5. **Finance and policy support.** Choose the support package the results lead with.
6. Press **Run model**, then read the **Results summary**.
7. Use **Uncertainty** to see which inputs move the answer, and **Methods, checks and
   sources** before you quote a number.

Each step has a *How to use this page* panel. Inputs carry a badge for their evidence
status: **Cited**, **Assumption** or **Placeholder**. Hover the help icon on any input
for its source.
""")

with st.expander("What is inside the model and what is not"):
    st.markdown("""
**Inside.** Mass and energy balance for every unit operation; equipment sizing and
factorial capital cost; reagent, utility, labour and maintenance cost; tax, depreciation
and working capital; capital grants, concessional debt and the CMPTI; scope 1, scope 2
and upstream emissions of purchased electricity, gas, reagents, resin, water and waste.

**Not inside.** Construction, equipment manufacture and decommissioning emissions;
transport of reagents and residues; land use; any impact category other than climate
change; carbon prices and emissions credits.

**Assumed, not modelled.** The host refinery supplies the liquor at a zero transfer price
and takes it back after gallium removal. No credit is taken for the sodium sulfate
returned to the host liquor.
""")

with st.expander("Developers"):
    st.markdown("""
**Charlie Lentfer** · lead developer, UNSW Sydney
**Rahman Daiyan** · supervisor, UNSW Sydney
""")

st.caption("OpenGa is a screening-level research model. The policy packages are "
           "hypothetical and no government has committed to them. Results are not "
           "investment advice. Read Methods, checks and sources before quoting a number.")
ui.footer()
