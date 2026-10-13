"""
Altair chart builders.

Palette is the validated three-slot categorical set (blue / orange / aqua),
which clears the all-pairs colour-vision and normal-vision floors on the light
surface. Aqua sits below 3:1 against the surface, so every chart that uses it
ships a legend AND the underlying table, which is the relief that WARN
requires.

House rules followed here: one y-axis per chart, never two; categorical hues
assigned in fixed order and never cycled; thin marks with a 2px gap between
stacked segments; recessive grid; a tooltip on every mark.
"""

from __future__ import annotations

import altair as alt
import pandas as pd

SERIES = ["#2a78d6", "#eb6834", "#1baf7a"]
DIVERGE_POS = "#e34948"
DIVERGE_NEG = "#2a78d6"
INK = "#0b0b0b"
INK2 = "#52514e"
GRID = "#e6e5e1"

_BASE = {
    "config": {
        "view": {"stroke": "transparent"},
        "axis": {"labelColor": INK2, "titleColor": INK2, "gridColor": GRID,
                 "domainColor": GRID, "tickColor": GRID, "labelFontSize": 11,
                 "titleFontSize": 11, "titleFontWeight": "normal"},
        "legend": {"labelColor": INK2, "titleColor": INK2, "labelFontSize": 11,
                   "titleFontSize": 11, "titleFontWeight": "normal"},
        "title": {"color": INK, "fontSize": 13, "fontWeight": 600, "anchor": "start"},
    }
}


def _cfg(c: alt.Chart) -> alt.Chart:
    return c.configure_view(stroke="transparent").configure_axis(
        labelColor=INK2, titleColor=INK2, gridColor=GRID, domainColor=GRID,
        tickColor=GRID, labelFontSize=11, titleFontSize=11, titleFontWeight="normal"
    ).configure_legend(
        labelColor=INK2, titleColor=INK2, labelFontSize=11, titleFontSize=11,
        titleFontWeight="normal", orient="top", direction="horizontal", offset=6
    ).configure_title(color=INK, fontSize=13, fontWeight=600, anchor="start").properties(
        # Streamlit defaults to autosize "fit", which squeezes title, legend and
        # axes into the stated height and flattens the plot. fit-x keeps the
        # container width and makes the stated height the plotting area.
        autosize=alt.AutoSizeParams(type="fit-x", contains="padding"),
        # Charts sit in white cards; without this the Streamlit theme paints the
        # page background behind the plot.
        background="#FFFFFF")


def stacked_by_unit(df: pd.DataFrame, value_cols: list[str], title: str,
                    y_title: str, order: list[str] | None = None,
                    names: dict | None = None, height: int = 260) -> alt.Chart:
    """Stacked column by unit operation. The first entry of ``value_cols`` sits
    on the baseline and the legend reads in the same order. Segments carry a
    2px surface gap so adjacent fills never touch."""
    long = df.melt(id_vars="unit", value_vars=value_cols,
                   var_name="component", value_name="value")
    long["pos"] = long["component"].map({c: i for i, c in enumerate(value_cols)})
    long["name"] = long["unit"].map(names or {}).fillna("")
    ch = (alt.Chart(long, title=title)
          .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4,
                    stroke="#FFFFFF", strokeWidth=2)
          .encode(
              x=alt.X("unit:N", sort=order or list(df["unit"]), title=None,
                      axis=alt.Axis(labelAngle=0)),
              y=alt.Y("value:Q", title=y_title, stack="zero"),
              color=alt.Color("component:N",
                              scale=alt.Scale(domain=value_cols, range=SERIES[:len(value_cols)]),
                              title=None),
              order=alt.Order("pos:Q", sort="ascending"),
              tooltip=[alt.Tooltip("unit:N", title="Unit"),
                       alt.Tooltip("name:N", title="Operation"),
                       alt.Tooltip("component:N", title="Component"),
                       alt.Tooltip("value:Q", title=y_title, format=",.2f")])
          .properties(height=height))
    return _cfg(ch)


def tornado(rows: list[dict], base: float, title: str, x_title: str) -> alt.Chart:
    """Swing about the base case. Diverging pair: blue below, red above."""
    recs = []
    for r in rows:
        for side, v in (("low", r["low"]), ("high", r["high"])):
            recs.append({"label": r["label"], "side": side, "value": v,
                         "delta": v - base, "swing": r["swing"],
                         "input": r["low_input"] if side == "low" else r["high_input"]})
    df = pd.DataFrame(recs)
    order = [r["label"] for r in rows]
    ch = (alt.Chart(df, title=title)
          .mark_bar(cornerRadius=4, height=16, stroke="#FFFFFF", strokeWidth=2)
          .encode(
              y=alt.Y("label:N", sort=order, title=None, axis=alt.Axis(labelLimit=260)),
              x=alt.X("delta:Q", title=x_title),
              color=alt.Color("side:N",
                              scale=alt.Scale(domain=["low", "high"],
                                              range=[DIVERGE_NEG, DIVERGE_POS]),
                              legend=alt.Legend(title=None,
                                                labelExpr="datum.label == 'low' "
                                                          "? 'Low input' : 'High input'")),
              tooltip=[alt.Tooltip("label:N", title="Input"),
                       alt.Tooltip("input:Q", title="Input value", format=",.4g"),
                       alt.Tooltip("value:Q", title="Result", format=",.2f"),
                       alt.Tooltip("delta:Q", title="Change vs base", format="+,.2f")])
          .properties(height=max(200, 28 * len(rows))))
    rule = alt.Chart(pd.DataFrame({"x": [0]})).mark_rule(
        color=INK2, strokeWidth=1).encode(x="x:Q")
    return _cfg(ch + rule)


def histogram(bins: list[dict], title: str, x_title: str,
              markers: dict[str, float] | None = None) -> alt.Chart:
    df = pd.DataFrame(bins)
    ch = (alt.Chart(df, title=title)
          # No corner radius: Vega-Lite 6 drops x/x2 range bars that carry one.
          # Bars run bin edge to bin edge ("from" to "to"), not from the midpoint.
          .mark_bar(stroke="#FFFFFF", strokeWidth=1.5, color=SERIES[0])
          .encode(
              x=alt.X("from:Q", title=x_title, bin="binned",
                      scale=alt.Scale(zero=False)),
              x2="to:Q",
              y=alt.Y("count:Q", title="Trials"),
              tooltip=[alt.Tooltip("from:Q", title="From", format=",.0f"),
                       alt.Tooltip("to:Q", title="To", format=",.0f"),
                       alt.Tooltip("count:Q", title="Trials"),
                       alt.Tooltip("share:Q", title="Share", format=".1%")])
          .properties(height=300))
    layers = [ch]
    if markers:
        md = pd.DataFrame([{"x": v, "label": k} for k, v in markers.items()])
        layers.append(alt.Chart(md).mark_rule(color=INK, strokeWidth=2,
                                              strokeDash=[4, 3])
                      .encode(x="x:Q",
                              tooltip=[alt.Tooltip("label:N"),
                                       alt.Tooltip("x:Q", format=",.1f")]))
        layers.append(alt.Chart(md).mark_text(align="left", dx=5, dy=-6,
                                              color=INK, fontSize=11)
                      .encode(x="x:Q", y=alt.value(0), text="label:N"))
    return _cfg(alt.layer(*layers))


def line(df: pd.DataFrame, x: str, y: str, title: str, x_title: str, y_title: str,
         point_col: str | None = None, marker_x: float | None = None) -> alt.Chart:
    ch = (alt.Chart(df, title=title)
          .mark_line(strokeWidth=2, color=SERIES[0], point=alt.OverlayMarkDef(
              color=SERIES[0], size=60, stroke="#FFFFFF", strokeWidth=2))
          .encode(
              x=alt.X(f"{x}:Q", title=x_title, scale=alt.Scale(zero=False)),
              y=alt.Y(f"{y}:Q", title=y_title, scale=alt.Scale(zero=False)),
              tooltip=[alt.Tooltip(f"{x}:Q", title=x_title, format=",.0f"),
                       alt.Tooltip(f"{y}:Q", title=y_title, format=",.2f")])
          .properties(height=320))
    layers = [ch]
    if marker_x is not None:
        md = pd.DataFrame({"x": [marker_x], "label": ["base case"]})
        layers.append(alt.Chart(md).mark_rule(color=INK2, strokeWidth=1,
                                              strokeDash=[4, 3]).encode(x="x:Q"))
        layers.append(alt.Chart(md).mark_text(align="left", dx=5, dy=-140,
                                              color=INK2, fontSize=11)
                      .encode(x="x:Q", text="label:N"))
    return _cfg(alt.layer(*layers))


def simple_bar(df: pd.DataFrame, x: str, y: str, title: str, x_title: str,
               y_title: str, horizontal: bool = True, fmt: str = ",.2f") -> alt.Chart:
    if horizontal:
        enc = dict(y=alt.Y(f"{x}:N", sort="-x", title=None),
                   x=alt.X(f"{y}:Q", title=y_title))
        h = max(200, 24 * len(df))
    else:
        enc = dict(x=alt.X(f"{x}:N", sort=None, title=None,
                           axis=alt.Axis(labelAngle=0)),
                   y=alt.Y(f"{y}:Q", title=y_title))
        h = 300
    ch = (alt.Chart(df, title=title)
          .mark_bar(cornerRadius=4, color=SERIES[0], stroke="#FFFFFF", strokeWidth=2)
          .encode(tooltip=[alt.Tooltip(f"{x}:N", title=x_title),
                           alt.Tooltip(f"{y}:Q", title=y_title, format=fmt)],
                  **enc)
          .properties(height=h))
    return _cfg(ch)


def grouped_bar(df: pd.DataFrame, cat: str, series: str, value: str, title: str,
                y_title: str, domain: list[str]) -> alt.Chart:
    ch = (alt.Chart(df, title=title)
          .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4,
                    stroke="#FFFFFF", strokeWidth=2)
          .encode(
              x=alt.X(f"{cat}:N", title=None, axis=alt.Axis(labelAngle=0)),
              y=alt.Y(f"{value}:Q", title=y_title),
              xOffset=alt.XOffset(f"{series}:N", sort=domain),
              color=alt.Color(f"{series}:N",
                              scale=alt.Scale(domain=domain, range=SERIES[:len(domain)]),
                              title=None),
              tooltip=[alt.Tooltip(f"{cat}:N"), alt.Tooltip(f"{series}:N"),
                       alt.Tooltip(f"{value}:Q", title=y_title, format=",.2f")])
          .properties(height=300))
    return _cfg(ch)


def waterfall(steps: list[dict], title: str, y_title: str) -> alt.Chart:
    """Policy contribution bridge."""
    df = pd.DataFrame(steps)
    ch = (alt.Chart(df, title=title)
          .mark_bar(cornerRadius=4, stroke="#FFFFFF", strokeWidth=2)
          .encode(
              x=alt.X("label:N", sort=list(df["label"]), title=None,
                      axis=alt.Axis(labelAngle=-20)),
              y=alt.Y("start:Q", title=y_title, scale=alt.Scale(zero=False)),
              y2="end:Q",
              color=alt.Color("kind:N",
                              scale=alt.Scale(domain=["level", "reduction"],
                                              range=[SERIES[0], SERIES[2]]),
                              title=None),
              tooltip=[alt.Tooltip("label:N", title="Step"),
                       alt.Tooltip("value:Q", title=y_title, format=",.2f")])
          .properties(height=320))
    return _cfg(ch)


# ---------------------------------------------------------------------------
# Added for the simplified V2 interface
# ---------------------------------------------------------------------------

SERIES4 = SERIES + ["#eda100"]      # fourth validated slot (yellow)
TOTAL = INK2                        # neutral for totals in a bridge


def lines_by_series(df: pd.DataFrame, x: str, y: str, series: str, domain: list[str],
                    colors: list[str], title: str, x_title: str, y_title: str,
                    marker_x: float | None = None, marker_label: str = "base case") -> alt.Chart:
    """One line per series, fixed colour per entity, legend on top. No end
    labels: the series converge at high assay and the labels collide."""
    base = alt.Chart(df)
    enc_color = alt.Color(f"{series}:N", scale=alt.Scale(domain=domain, range=colors),
                          title=None)
    lines = base.mark_line(strokeWidth=2).encode(
        x=alt.X(f"{x}:Q", title=x_title, scale=alt.Scale(zero=False)),
        y=alt.Y(f"{y}:Q", title=y_title, scale=alt.Scale(zero=False)),
        color=enc_color)
    pts = base.mark_point(filled=True, size=64, stroke="#FFFFFF", strokeWidth=2,
                          opacity=1).encode(
        x=f"{x}:Q", y=f"{y}:Q", color=enc_color,
        tooltip=[alt.Tooltip(f"{series}:N", title="Policy"),
                 alt.Tooltip(f"{x}:Q", title=x_title, format=",.0f"),
                 alt.Tooltip(f"{y}:Q", title=y_title, format=",.0f")])
    layers = [lines, pts]
    if marker_x is not None:
        md = pd.DataFrame({"x": [marker_x], "label": [marker_label]})
        layers.append(alt.Chart(md).mark_rule(color=INK2, strokeWidth=1,
                                              strokeDash=[4, 3]).encode(x="x:Q"))
        layers.append(alt.Chart(md).mark_text(align="left", dx=5, baseline="top",
                                              color=INK2, fontSize=11)
                      .encode(x="x:Q", y=alt.value(4), text="label:N"))
    return _cfg(alt.layer(*layers, title=title).properties(height=280))


def bridge(steps: list[dict], title: str, y_title: str) -> alt.Chart:
    """Build-up of a total from additive parts. Each step: label, value (signed),
    kind in {'add', 'subtract', 'total'}. Values print above each bar."""
    rows, run = [], 0.0
    for s in steps:
        if s["kind"] == "total":
            start, end = 0.0, s["value"]
        else:
            start, end = run, run + s["value"]
            run = end
        rows.append({"label": s["label"], "start": start, "end": end,
                     "top": max(start, end), "value": s["value"], "kind": s["kind"],
                     "text": (f"{s['value']:,.0f}" if s["kind"] != "subtract"
                              else f"−{abs(s['value']):,.0f}")})
    df = pd.DataFrame(rows)
    order = list(df["label"])
    dom = ["add", "subtract", "total"]
    rng = [SERIES[0], SERIES[2], TOTAL]
    bars = alt.Chart(df).mark_bar(cornerRadius=4, size=56, stroke="#FFFFFF",
                                  strokeWidth=2).encode(
        x=alt.X("label:N", sort=order, title=None,
                axis=alt.Axis(labelAngle=0, labelLimit=160)),
        y=alt.Y("start:Q", title=y_title),
        y2="end:Q",
        color=alt.Color("kind:N", scale=alt.Scale(domain=dom, range=rng), legend=None),
        tooltip=[alt.Tooltip("label:N", title="Component"),
                 alt.Tooltip("value:Q", title=y_title, format=",.2f")])
    text = alt.Chart(df).mark_text(dy=-8, fontSize=12, color=INK).encode(
        x=alt.X("label:N", sort=order), y="top:Q", text="text:N")
    return _cfg(alt.layer(bars, text, title=title).properties(height=280))


def stacked_hbar(df: pd.DataFrame, cat: str, value_cols: list[str], title: str,
                 x_title: str, order: list[str] | None = None) -> alt.Chart:
    """Horizontal stacked bars, one row per category."""
    long = df.melt(id_vars=cat, value_vars=value_cols, var_name="component",
                   value_name="value")
    long["pos"] = long["component"].map({c: i for i, c in enumerate(value_cols)})
    ch = (alt.Chart(long, title=title)
          .mark_bar(cornerRadiusTopRight=4, cornerRadiusBottomRight=4, size=22,
                    stroke="#FFFFFF", strokeWidth=2)
          .encode(
              y=alt.Y(f"{cat}:N", sort=order or list(df[cat]), title=None),
              x=alt.X("value:Q", title=x_title, stack="zero"),
              color=alt.Color("component:N",
                              scale=alt.Scale(domain=value_cols,
                                              range=SERIES[:len(value_cols)]),
                              title=None),
              order=alt.Order("pos:Q", sort="ascending"),
              tooltip=[alt.Tooltip(f"{cat}:N", title=cat),
                       alt.Tooltip("component:N", title="Component"),
                       alt.Tooltip("value:Q", title=x_title, format=",.2f")])
          .properties(height=max(120, 40 * len(df))))
    return _cfg(ch)


def bridge_compare(packages: list[dict], selected: str, colors: dict, title: str,
                   subtitle: str, y_title: str) -> alt.Chart:
    """LCOP build-up for several policy packages side by side.

    ``packages``: [{"name", "steps": [{"label", "value", "kind"}]}]. The selected
    package is drawn solid in its colour; the others as dashed outlines in theirs.
    A bar is labelled when it is the selected package's, or when its value
    differs from the selected package's at that step."""
    names = [p["name"] for p in packages]
    order = list(dict.fromkeys(s["label"] for p in packages for s in p["steps"]))
    sel_vals = {s["label"]: s["value"] for p in packages if p["name"] == selected
                for s in p["steps"]}
    rows = []
    for p in packages:
        run = 0.0
        for s in p["steps"]:
            if s["kind"] == "total":
                start, end = 0.0, s["value"]
            else:
                start, end = run, run + s["value"]
                run = end
            if abs(s["value"]) < 0.005 and s["kind"] != "total":
                continue
            is_sel = p["name"] == selected
            differs = abs(s["value"] - sel_vals.get(s["label"], float("nan"))) > 0.5 \
                if s["label"] in sel_vals else True
            rows.append({"pkg": p["name"], "label": s["label"], "start": start, "end": end,
                         "top": max(start, end), "value": s["value"], "sel": is_sel,
                         "show": is_sel or differs,
                         "text": (f"{s['value']:,.0f}" if s["kind"] != "subtract"
                                  else f"−{abs(s['value']):,.0f}")})
    df = pd.DataFrame(rows)
    rng = [colors[n] for n in names]
    x = alt.X("label:N", sort=order, title=None,
              axis=alt.Axis(labelAngle=0, labelLimit=160),
              scale=alt.Scale(paddingInner=0.22))
    xo = alt.XOffset("pkg:N", sort=names, scale=alt.Scale(domain=names, paddingInner=0.12))
    tip = [alt.Tooltip("pkg:N", title="Package"), alt.Tooltip("label:N", title="Component"),
           alt.Tooltip("value:Q", title=y_title, format=",.2f")]
    solid = alt.Chart(df[df["sel"]]).mark_bar(cornerRadius=3).encode(
        x=x, xOffset=xo, y=alt.Y("start:Q", title=y_title), y2="end:Q",
        color=alt.Color("pkg:N", scale=alt.Scale(domain=names, range=rng), title=None,
                        sort=names),
        tooltip=tip)
    dashed = alt.Chart(df[~df["sel"]]).mark_bar(
        cornerRadius=3, fill="#FFFFFF", strokeDash=[5, 3], strokeWidth=1.8).encode(
        x=x, xOffset=xo, y="start:Q", y2="end:Q",
        stroke=alt.Stroke("pkg:N", scale=alt.Scale(domain=names, range=rng), title=None,
                          sort=names),
        tooltip=tip)
    # Same colour encoding as the solid layer, so the two share one legend.
    text = alt.Chart(df[df["show"]]).mark_text(dy=-7, fontSize=11).encode(
        x=x, xOffset=xo, y="top:Q", text="text:N",
        color=alt.Color("pkg:N", scale=alt.Scale(domain=names, range=rng), title=None,
                        sort=names))
    t = alt.TitleParams(title, subtitle=[subtitle], subtitleColor=INK2, subtitleFontSize=11,
                        subtitleFontWeight="normal")
    return _cfg(alt.layer(dashed, solid, text, title=t).properties(height=300))
