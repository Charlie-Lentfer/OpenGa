"""
OpenGa — cost and emissions of primary gallium recovery from an Australian
Bayer liquor slipstream. UNSW Sydney open-access research model.

Run:   streamlit run app/streamlit_app.py

Layout
------
An Overview page, five "Build the scenario" steps and three results pages,
styled to match the UNSW copper value-chain tool. Inputs are edited on the
step pages; nothing is calculated until the user presses Run model, and every
results panel is computed from that Run's snapshot (see ``state.py``). If
inputs change after a run, results stay visible behind a stale banner.

The app reports one cost, the levelised cost of production (LCOP): the
constant real price per kilogram at which the plant earns its cost of capital
after company tax (``finance.pstar``). No model equation lives in the app.
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

APP = Path(__file__).resolve().parent
for p in (APP.parent, APP):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import state  # noqa: E402
import ui  # noqa: E402

st.set_page_config(page_title="OpenGa · Gallium Recovery Assessment",
                   page_icon=str(APP / "assets" / "unsw_favicon.png"),
                   layout="wide", initial_sidebar_state="auto")

state.init()
ui.apply_style()

V = APP / "views"
pg = st.navigation({
    "Start": [
        st.Page(V / "overview.py", title="Overview", icon=":material/home:", default=True),
    ],
    "Build the scenario": [
        st.Page(V / "feed.py", title="1. Feed liquor and plant basis", icon=":material/water_drop:"),
        st.Page(V / "process.py", title="2. Gallium recovery process", icon=":material/science:"),
        st.Page(V / "cost.py", title="3. Capital and operating cost", icon=":material/payments:"),
        st.Page(V / "carbon.py", title="4. Energy and carbon", icon=":material/bolt:"),
        st.Page(V / "policy.py", title="5. Finance and policy support",
                icon=":material/account_balance:"),
    ],
    "Results": [
        st.Page(V / "results.py", title="Results summary", icon=":material/insights:"),
        st.Page(V / "uncertainty.py", title="Uncertainty", icon=":material/stacked_line_chart:"),
        st.Page(V / "methods.py", title="Methods, checks and sources",
                icon=":material/menu_book:"),
    ],
})

with st.sidebar:
    st.markdown(f"<div class='ga-sidebrand'>{ui.PRODUCT} {ui.VERSION}"
                "<span>Gallium recovery from Bayer liquor</span></div>",
                unsafe_allow_html=True)
    st.write("")
    if not state.has_run():
        st.info("Not run yet. Every input starts at its published default.",
                icon=":material/info:")
    elif state.is_stale():
        st.warning("Inputs changed since the last run.", icon=":material/update:")
    else:
        st.success(f"Results up to date · run at {st.session_state.run['at']}",
                   icon=":material/check_circle:")
    state.run_button("sidebar", stretch=True)
    n = state.n_edited()
    st.caption(f"{n} input{'s' if n != 1 else ''} changed from the defaults · "
               f"policy: {state.package_name(of_run=False)}")
    st.button("Reset to published defaults", key="reset_all", on_click=state.reset_all,
              icon=":material/restart_alt:", width="stretch")

pg.run()
