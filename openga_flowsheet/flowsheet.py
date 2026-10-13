"""Model-driven OpenGa overview. Standard library only; no geometry file required.

Amounts retain the model basis (kg per kg of 4N gallium product). Groups are
presentation summaries, not physical mixed streams. The S30P purge is shown at
the neutralisation interface; no downstream treatment balance is inferred.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from html import escape
import math
from uuid import uuid4

COMPONENT_KEYS = {
    "total": ("total_kg_per_kg_Ga", "Total mass"),
    "Ga": ("Ga", "Gallium"),
    "Al": ("Al", "Aluminium"),
    "V": ("V", "Vanadium"),
}
BASIS = "kg per kg of 4N gallium product"


@dataclass(frozen=True)
class StreamGroup:
    key: str
    label: str
    detail: str
    ids: tuple[str, ...]
    kind: str = "input"


INPUTS = (
    StreamGroup("feed", "Bayer liquor", "From the alumina refinery", ("S1",)),
    StreamGroup("water", "Raw water", "Water treatment and process supply", ("S10",)),
    StreamGroup("sulfuric", "Sulfuric acid", "Eluant preparation", ("S9",)),
    StreamGroup("caustic", "Caustic soda solution", "Precipitation and purification", ("S20", "S24")),
    StreamGroup("lime", "Lime · CaO", "Purification reagent", ("S25",)),
    StreamGroup("resin", "Fresh resin", "Ion exchange make-up", ("S17",)),
    StreamGroup("hcl", "Hydrochloric acid", "Refining reagent", ("S32",)),
)
OUTPUTS = (
    StreamGroup("product", "4N gallium", "Final product", ("S34",), "product"),
    StreamGroup("liquor_return", "Ga-depleted liquor", "Return to the alumina refinery", ("S4",), "return"),
    StreamGroup("filter_return", "Filter residue", "Return to the alumina refinery", ("S2",), "return"),
    StreamGroup("liquid_return", "Other refinery returns", "Wash waste and centrate", ("S7", "S22"), "return"),
    StreamGroup("wastewater", "Wastewater / condensate", "Treatment reject and regeneration", ("S11", "S18", "S26"), "waste"),
    StreamGroup("residues", "Resin, cake and residues", "Spent resin, purification and refining", ("S19", "S27", "S33"), "waste"),
    StreamGroup("purge", "Electrolyte purge", "To neutralisation", ("S30P",), "waste"),
    StreamGroup("vents", "Gas / mist outlets", "Cell gases and acid mist to absorption", ("S29", "S12"), "waste"),
)

STAGES = (
    ("Feed preparation", "Filter press", "UP1"),
    ("Ion exchange cycle", "Adsorption · washing · elution · regeneration", "UP2 / 3 / 5 / 6"),
    ("Precipitation & separation", "Precipitation · centrifugation", "UP7 / 8"),
    ("Purification", "Electrolyte preparation", "UP9"),
    ("Electrowinning", "Gallium metal recovery", "UP10"),
    ("Refining", "Final gallium purification", "UP11"),
)

THEMES = {
    "light": dict(bg="#F7F9FB", surface="#FFFFFF", ink="#172C3D", muted="#52697B",
                  border="#DAE3EA", input="#3575A1", soft="#EAF2F8", accent="#127A69",
                  product="#E9F6F0", waste="#99723C", line="#AABEC9"),
    "dark": dict(bg="#111C27", surface="#1B2A38", ink="#ECF2F7", muted="#A9BBC9",
                 border="#344859", input="#8FC6EC", soft="#223A4C", accent="#7CDBC0",
                 product="#1B3B36", waste="#DCB77D", line="#5C788B"),
}


def as_dict(streams) -> dict:
    """Accept an ID-keyed mapping, a list of records, or the supplied JSON wrapper."""
    if isinstance(streams, Mapping) and "streams" in streams:
        streams = streams["streams"]
    if isinstance(streams, (list, tuple)):
        result = {}
        for record in streams:
            if not isinstance(record, Mapping) or "id" not in record:
                raise ValueError("Every stream record must contain an 'id'.")
            if record["id"] in result:
                raise ValueError(f"Duplicate stream ID: {record['id']}")
            result[record["id"]] = dict(record)
        return result
    if not isinstance(streams, Mapping):
        raise TypeError("streams must be a mapping, a list, or a JSON stream register.")
    if any(not isinstance(v, Mapping) for v in streams.values()):
        raise TypeError("Each stream value must be a record mapping.")
    return {k: dict(v) for k, v in streams.items()}


def _number(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        value = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return value if math.isfinite(value) else None


def fmt(value) -> str:
    value = _number(value)
    if value is None:
        return "—"
    if value == 0:
        return "0"
    a = abs(value)
    if a >= 1000:
        return f"{value:,.0f}"
    if a >= 10:
        return f"{value:,.1f}"
    if a >= 0.01:
        return f"{value:.3f}"
    return f"{value:.2e}"


def stream_value(record, component="total"):
    """Missing is unknown, not zero. Prefer the model's elemental equivalents."""
    field = COMPONENT_KEYS[component][0]
    if record is None:
        return None
    if field in record:
        return _number(record[field])
    components = record.get("components")
    if component != "total" and isinstance(components, Mapping) and component in components:
        return _number(components[component])
    return None


def group_value(streams, group, component="total"):
    values = [stream_value(streams.get(sid), component) for sid in group.ids]
    return None if any(v is None for v in values) else math.fsum(values)


def overview_rows(streams, component="total"):
    """A matching accessible table, using the exact same groups as the drawing."""
    streams = as_dict(streams)
    return [dict(direction=direction, label=g.label, destination=g.detail,
                 streams=", ".join(g.ids), value=group_value(streams, g, component))
            for direction, groups in (("Input", INPUTS), ("Output / treatment interface", OUTPUTS))
            for g in groups]


def _tooltip(streams, group, component, basis=BASIS):
    lines = [group.label, group.detail, f"Basis: {basis}"]
    for sid in group.ids:
        record = streams.get(sid, {})
        lines.append(f"{sid} · {record.get('description', 'Missing stream')} · "
                     f"{fmt(stream_value(record, component))} kg")
    if len(group.ids) > 1:
        lines.append("Grouped for presentation; separate physical streams.")
    return "\n".join(lines)


def render_svg(streams, component="total", theme="light", basis=BASIS,
               geometry=None, show_zero=True, interactive=True) -> str:
    """Render a scalable overview with live values and boundary-stream tooltips.

    geometry is accepted for old call sites but the overview uses its own layout.
    show_zero=False hides zero-valued groups; missing values always remain visible.
    Internal stream records are never rendered or included in group totals.
    Set interactive=False for image embedding, which has no per-card tooltips.
    """
    if component not in COMPONENT_KEYS:
        raise ValueError(f"Unknown component: {component}. Choose {tuple(COMPONENT_KEYS)}")
    if theme not in THEMES:
        raise ValueError("theme must be 'light' or 'dark'.")
    s, c = as_dict(streams), THEMES[theme]
    uid = "og-" + uuid4().hex[:12]
    esc = lambda value: escape(str(value), quote=True)
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1440 1080" '
         f'width="1440" height="1080" role="img" aria-labelledby="{uid}-title {uid}-desc" '
         'style="display:block;width:100%;height:auto;font-family:Inter,ui-sans-serif,system-ui,-apple-system,Segoe UI,sans-serif">',
         f'<title id="{uid}-title">OpenGa process overview · {COMPONENT_KEYS[component][1]}</title>',
         f'<desc id="{uid}-desc">Major inputs and outputs around six processing stages. '
         'Arrows indicate process sequence, not individual pipes. Internal streams and recycle are omitted.</desc>',
         f'<defs><marker id="{uid}-arrow" markerWidth="6" markerHeight="6" '
         f'refX="5" refY="3" orient="auto"><path d="M0 0L5 3L0 6" '
         f'fill="none" stroke="{c["line"]}" stroke-width="1.3"/></marker></defs>',
         f'<style>#{uid} .og-card:hover rect,#{uid} .og-card:focus rect{{stroke:{c["input"]};stroke-width:1.8}}'
         f'#{uid} text{{font-variant-numeric:tabular-nums}}'
         f'#{uid} .og-card:focus{{outline:none}}</style>', f'<g id="{uid}">']

    def rect(x, y, w, h, fill, stroke=None, radius=14):
        o.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" '
                 f'fill="{fill}" stroke="{stroke or fill}"/>')

    def text(x, y, content, size=14, color=None, weight=400, anchor="start", **attrs):
        more = " ".join(f'{k.replace("_", "-")}="{esc(v)}"' for k, v in attrs.items())
        o.append(f'<text x="{x}" y="{y}" fill="{color or c["ink"]}" font-size="{size}" '
                 f'font-weight="{weight}" text-anchor="{anchor}" {more}>{esc(content)}</text>')

    def line(x1, y1, x2, y2, arrow=False):
        marker = f' marker-end="url(#{uid}-arrow)"' if arrow else ""
        o.append(f'<path d="M{x1} {y1}L{x2} {y2}" fill="none" stroke="{c["line"]}" '
                 f'stroke-width="1.5"{marker}/>')

    rect(0, 0, 1440, 1080, c["bg"], radius=20)
    rect(40, 36, 42, 42, c["accent"], radius=12)
    text(61, 64, "Ga", 20, c["bg"], 700, "middle")
    text(96, 52, "OPENGA  /  PROCESS OVERVIEW", 12, c["muted"], 650, letter_spacing=1.6)
    text(96, 87, "Gallium recovery flowsheet", 30, weight=650)
    text(40, 119, basis, 14, c["muted"])
    rect(1204, 46, 196, 34, c["soft"], radius=17)
    text(1302, 68, COMPONENT_KEYS[component][1], 13, c["input"], 650, "middle")

    feed_ga = stream_value(s.get("S1"), "Ga")
    product_ga = stream_value(s.get("S34"), "Ga")
    recovery = (100 * product_ga / feed_ga
                if feed_ga is not None and feed_ga > 0 and product_ga is not None else None)
    metrics = ((40, "GALLIUM IN FEED", f"{fmt(feed_ga)} kg", "Elemental Ga in Bayer liquor"),
               (503, "OVERALL Ga RECOVERY", "—" if recovery is None else f"{recovery:.1f}%", "Product Ga / feed Ga"),
               (966, "GALLIUM IN PRODUCT", f"{fmt(product_ga)} kg", "Elemental Ga in final product"))
    for x, label, value, detail in metrics:
        rect(x, 145, 434, 94, c["surface"], c["border"])
        text(x + 20, 169, label, 11, c["muted"], 650, letter_spacing=1.2)
        text(x + 20, 205, value, 27, c["accent"], 650)
        text(x + 20, 224, detail, 12, c["muted"])

    text(40, 281, "MAJOR INPUTS", 12, c["input"], 700, letter_spacing=1.5)
    text(460, 281, "PROCESS", 12, c["muted"], 700, letter_spacing=1.5)
    text(1020, 281, "PRODUCTS & OUTLETS", 12, c["accent"], 700, letter_spacing=1.5)
    line(390, 276, 435, 276, True)
    line(965, 276, 1005, 276, True)

    def card(x, y, w, group):
        value = group_value(s, group, component)
        product = group.kind == "product"
        color = c["accent"] if product or group.kind == "return" else c["input"] if group.kind == "input" else c["waste"]
        tip = _tooltip(s, group, component, basis)
        o.append(f'<g class="og-card" tabindex="0" role="group" aria-label="{esc(tip)}" '
                 f'data-group="{group.key}"><title>{esc(tip)}</title>')
        rect(x, y, w, 73, c["product"] if product else c["surface"], c["accent"] if product else c["border"], 10)
        o.append(f'<circle cx="{x+18}" cy="{y+24}" r="3.5" fill="{color}"/>')
        text(x + 30, y + 27, group.label, 14, weight=650)
        # Values get a dedicated line to keep labels readable at narrow app widths.
        text(x + 30, y + 48, f"{fmt(value)} kg", 18, color, 650)
        text(x + 30, y + 64, group.detail, 10.7, c["muted"])
        o.append('</g>')

    for x, w, groups in ((40, 350, INPUTS), (1020, 380, OUTPUTS)):
        visible = [g for g in groups if show_zero or group_value(s, g, component) != 0]
        for i, group in enumerate(visible):
            card(x, 306 + i * 82, w, group)

    for i, (name, subtitle, units) in enumerate(STAGES):
        y = 306 + i * 101
        if i:
            line(725, y - 15, 725, y - 3, True)
        rect(460, y, 530, 84, c["surface"], c["border"], 12)
        rect(476, y + 20, 42, 42, c["soft"], radius=11)
        text(497, y + 47, f"{i+1:02d}", 15, c["input"], 650, "middle")
        text(533, y + 28, name, 18, weight=650)
        text(533, y + 50, subtitle, 12, c["muted"])
        text(533, y + 70, units, 10, c["muted"], 600, letter_spacing=.7)

    rect(460, 924, 530, 76, c["soft"], radius=12)
    text(480, 949, "UP4  /  WATER & ACID PREPARATION", 11, c["input"], 700, letter_spacing=.7)
    text(480, 971, "Water softening and eluant make-up", 14, weight=550)
    text(480, 988, "Supports the ion exchange cycle and purification", 11, c["muted"])

    text(40, 927, "INPUT BASIS", 10, c["muted"], 700, letter_spacing=1)
    text(40, 948, "Reagent amounts follow the supplied model.", 12, c["muted"])
    text(40, 967, "Grouped values are presentation totals.", 12, c["muted"])
    text(1020, 990, "Purge is shown at the neutralisation interface.", 11, c["muted"])
    line(40, 1020, 1400, 1020)
    text(40, 1048, "Process sequence only · internal streams and recycle omitted", 12, c["muted"])
    footer = ("Hover cards for source streams · — = unavailable" if interactive else
              "Grouped input / output values · — = unavailable")
    text(1400, 1048, footer, 12, c["muted"], anchor="end")
    o.extend(['</g>', '</svg>'])
    return "\n".join(o)


def render_html(streams, component="total", theme="light", **kwargs):
    """Script-free iframe document; scrolls horizontally in narrow tabs."""
    svg = render_svg(streams, component=component, theme=theme, **kwargs)
    return ('<!doctype html><html><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>OpenGa process overview</title>'
            '<style>html,body{margin:0;padding:0;background:transparent}</style></head><body>'
            '<div style="width:100%;max-width:1440px;margin:auto;overflow-x:auto;border-radius:16px" '
            'tabindex="0" aria-label="Scrollable OpenGa flowsheet">'
            f'<div style="min-width:1100px">{svg}</div></div></body></html>')


def streamlit_flowsheet(streams, key="fs"):
    """Compatibility entry point for the original integration."""
    if __package__:
        from .app_flowsheet_tab import flowsheet_tab
    else:
        from app_flowsheet_tab import flowsheet_tab
    return flowsheet_tab(streams, key=key)
