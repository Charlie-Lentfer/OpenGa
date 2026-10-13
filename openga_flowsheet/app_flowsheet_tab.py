"""Display the live V2 flowsheet with flowsheet_tab(results.streams)."""
from __future__ import annotations

import streamlit as st

if __package__:
    from .flowsheet import as_dict, COMPONENT_KEYS, overview_rows, render_html, render_svg
else:
    from flowsheet import as_dict, COMPONENT_KEYS, overview_rows, render_html, render_svg


def flowsheet_tab(streams, *, key="openga_flowsheet", theme="light", show_details=True,
                  display_mode="image"):
    """Display the current result on each Streamlit rerun.

    Supply a unique key for each instance. Live streams are required;
    an empty live result is never replaced by demonstration data.
    This function does not call set_page_config or alter global app styling.
    display_mode="image" displays a responsive SVG image; model values still
    update on rerun, but individual card hover tooltips are unavailable.
    """
    if display_mode not in ("interactive", "image"):
        raise ValueError("display_mode must be 'interactive' or 'image'.")
    s = as_dict(streams)
    c1, c2, c3 = st.columns([2, 1, 3])
    component = c1.selectbox("Display quantity", list(COMPONENT_KEYS),
                           format_func=lambda k: COMPONENT_KEYS[k][1], key=f"{key}_component")
    selected_theme = c2.selectbox("Appearance", ["light", "dark"],
                                  index=["light", "dark"].index(theme),
                                  format_func=str.title, key=f"{key}_theme")
    svg = render_svg(s, component=component, theme=selected_theme,
                     interactive=display_mode == "interactive")
    if display_mode == "image":
        c3.caption("SVG image · scales to fit your app and updates with the model. "
                   "Source streams are listed in the table below.")
        # Passing SVG text avoids any local file path in the deployed app.
        # An integer width supports both current and older Streamlit releases.
        st.image(svg, width=1440)
    else:
        c3.caption("Values update with your model. Hover a card for its source streams. "
                   "In narrow panels, scroll the diagram horizontally.")
        html = render_html(s, component=component, theme=selected_theme)
        # st.html sanitizes away inline SVG. An iframe preserves vector graphics,
        # native tooltips and keyboard focus without changing the host app's CSS.
        if hasattr(st, "iframe"):
            st.iframe(html, height="content")
        else:
            import streamlit.components.v1 as components
            components.html(html, height=1100, scrolling=True)
    st.download_button("Download SVG", svg,
                       file_name=f"openga_overview_{component}_{selected_theme}.svg",
                       mime="image/svg+xml", key=f"{key}_download")
    if show_details:
        with st.expander("Major input and output values"):
            rows = overview_rows(s, component)
            st.dataframe([{"Direction": r["direction"], "Group": r["label"],
                           "Description": r["destination"], "Source streams": r["streams"],
                           "kg per kg 4N Ga": r["value"]} for r in rows],
                         hide_index=True)
            st.caption("Groups are summaries of separate streams. The electrolyte purge is reported "
                       "at the neutralisation interface; S30 and S30R are excluded. "
                       "Reagent values retain the original model's mass basis.")
    return s

