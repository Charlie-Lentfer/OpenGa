"""Step 4: electricity supply and emission factors."""

import pandas as pd
import streamlit as st

import state
import ui
from openga_v1.config import UNIT_OPS
from openga_v1.energy import ROUTES

ui.step_intro(
    "4. Energy and carbon",
    "Sets where the plant's electricity comes from and the emission factors applied to "
    "electricity, gas, reagents and waste. The supply mix changes both the carbon result "
    "and, if you connect it, the electricity price used in the cost model.",
    "scope 1 + 2 and all-boundary carbon intensity per kilogram, the blended electricity "
    "price, and emissions by unit operation.")

ui.how_to(
    ["Set the **delivered shares** of grid, behind-the-meter solar, solar plus battery, "
     "direct wind and onsite gas. They must sum to 100%.",
     "Check the route prices and battery settings if you use solar plus battery.",
     "Decide whether the blended price should replace the base electricity price in the "
     "cost model (**Financial connection**).",
     "Review the emission factors. Grid and gas factors are Australian national factors; "
     "embodied factors are proxies.",
     "Press **Run model** to see the carbon result."],
    ["Scope 1 + 2 and all-boundary carbon intensity per kilogram of gallium.",
     "Blended electricity price and emissions intensity against a 100% grid supply.",
     "Emissions by unit operation and the electricity route register."],
    "Shares are annual totals only. The model does no dispatch, firming or storage sizing.")

st.subheader("Inputs")
p = state.current_inputs().params
share = sum(p[k] for _, _, k in ROUTES)
if abs(share - 1) > 1e-6:
    st.error(f"The delivered shares sum to {share * 100:,.1f}%. Set them to sum to 100% "
             "before you run.", icon=":material/error:")
state.input_sections([("Energy mix", "Delivered shares"),
                      ("Energy mix", "Route prices"),
                      ("Energy mix", "Battery storage"),
                      ("Energy mix", "Financial connection"),
                      ("Carbon", "Electricity and fuel factors"),
                      ("Carbon", "Renewable and battery embodied factors"),
                      ("Carbon", "Embodied chemical and waste factors"),
                      ("Carbon", "Allocation")])
state.run_footer("carbon")

st.subheader("Carbon results")
box = state.results_container()
if box is None:
    ui.empty_state("Press **Run model** to calculate carbon intensity for this supply mix.")
else:
    with box:
        R = state.results()
        en, cb = R.energy, R.carbon
        if not en.valid:
            st.error(en.invalid_reason)
        c = st.columns(3)
        c[0].metric("Scope 1 + 2 (kg CO₂e per kg Ga)", f"{cb.scope12:,.1f}",
                    help="Site fuel and purchased electricity. Rests on published "
                         "Australian factors.")
        c[1].metric("All boundaries (kg CO₂e per kg Ga)", f"{cb.total:,.1f}",
                    delta=(f"{cb.total - cb.ref_total:+,.1f} vs 100% grid"
                           if abs(cb.total - cb.ref_total) > 0.05 else None),
                    delta_color="inverse",
                    help="Adds grid losses, fuel supply and embodied chemicals, water and "
                         "waste on proxy factors.")
        c[2].metric("Blended electricity price (A$/MWh)", f"{en.mix_price:,.0f}",
                    delta=(f"{en.mix_price - en.grid_price:+,.0f} vs 100% grid"
                           if abs(en.mix_price - en.grid_price) > 0.5 else None),
                    delta_color="inverse")
        if not en.use_mix and abs(en.mix_price - en.grid_price) > 0.5:
            st.caption("The blended price is not feeding the cost model. Turn on the "
                       "financial connection above to use it.")

        with st.expander("Emissions by unit operation"):
            ui.table(pd.DataFrame([{
                "Unit": u, "Operation": nm,
                "Electricity (kWh/kg)": cb.by_up[u]["electricity_kwh"],
                "Scope 1": cb.by_up[u]["scope1"], "Scope 2": cb.by_up[u]["scope2"],
                "Upstream": cb.by_up[u]["upstream"], "Total": cb.by_up[u]["total"],
                "Share": cb.by_up[u]["total"] / cb.total if cb.total else 0}
                for u, nm in UNIT_OPS]),
                {"Electricity (kWh/kg)": "{:,.2f}", "Scope 1": "{:,.2f}",
                 "Scope 2": "{:,.2f}", "Upstream": "{:,.2f}", "Total": "{:,.2f}",
                 "Share": "{:.1%}"})
            st.caption("kg CO₂e per kg Ga. The same split is charted on the Results summary.")

        with st.expander("Electricity route register"):
            ui.table(pd.DataFrame([{"Route": rt.name, "Share": rt.share,
                                    "Price (A$/MWh)": rt.price, "Scope 1": rt.ef_s1,
                                    "Scope 2": rt.ef_s2, "Upstream": rt.ef_up,
                                    "Status": rt.status, "Source": rt.source}
                                   for rt in en.routes]),
                     {"Share": "{:.0%}", "Price (A$/MWh)": "{:,.0f}", "Scope 1": "{:.3f}",
                      "Scope 2": "{:.3f}", "Upstream": "{:.3f}"})
            st.caption("kg CO₂e per kWh delivered. Generator efficiency and battery "
                       "round-trip losses are applied once, here.")

        with st.expander("Boundary: what is inside and what is not"):
            st.markdown("""
**Inside.** Onsite fuel combustion (scope 1). Purchased electricity and steam (scope 2).
Upstream and embodied emissions for grid losses, gas supply, renewable and battery
manufacture, and the purchased acid, caustic, lime, HCl, resin, water, reject and solid
residue the mass balance quantifies.

**Outside.** Construction and equipment manufacture, decommissioning, staff transport,
reagent and residue transport, refrigerants, land use, and every impact category other
than global warming.

**The Bayer liquor carries zero upstream burden** by cut-off. An economic or mass
allocation would load part of the alumina footprint onto the gallium, and it would not
be small. No credit is taken for the sodium sulfate returned to the host circuit.

This is a screening inventory, not a product LCA.
""")
ui.footer()
