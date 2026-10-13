"""
Process flow diagram for the Process page, drawn as SVG.

The layout follows the project's own block flow diagram: one vertical spine
from the refinery to 4N gallium, side streams numbered as in the stream
register (S1 to S34), wastes in red. Quantities are not printed on the drawing;
each stream and unit carries a hover tooltip with its live values, and the full
stream table sits under the diagram.

Pure string building, no model logic. ``svg()`` takes the stream register and
the MEB result from ``engine.run`` and returns a standalone SVG document.
"""

from __future__ import annotations

from html import escape

INK = "#1F2A44"
TAG = "#5A6577"
WASTE = "#B42318"
SOURCE_FILL = "#EEF0F2"
PRODUCT_FILL = "#2F6FC9"
FONT = "'Source Sans 3', 'Source Sans Pro', 'Helvetica Neue', Arial, sans-serif"

W, H = 900, 1300
CX = 500                     # spine centre
BW, BH = 210, 56             # unit box
SIDE_W = 200                 # UP4 and UP6 boxes
UP4_CX, UP6_CX = 230, 790

ROWS = {"SRC": 24, "UP1": 150, "UP2": 260, "UP3": 370, "UP5": 520, "UP7": 660,
        "UP8": 770, "UP9": 880, "UP10": 1000, "UP11": 1110, "PRODUCT": 1220}
ROWS["UP4"] = ROWS["UP6"] = ROWS["UP5"]

NAMES = {"UP1": "Filter press", "UP2": "Ion exchange", "UP3": "Washing",
         "UP4": "Softening & acid make-up", "UP5": "Elution", "UP6": "Regeneration",
         "UP7": "Precipitation", "UP8": "Centrifuge", "UP9": "Purification",
         "UP10": "Electrowinning", "UP11": "Refining"}


def _fmt(x: float) -> str:
    if x == 0:
        return "0"
    if abs(x) >= 100:
        return f"{x:,.0f}"
    if abs(x) >= 1:
        return f"{x:,.2f}"
    return f"{x:,.4f}"


class _Pen:
    def __init__(self, streams: dict | None, meb=None):
        self.s = streams or {}
        self.meb = meb
        self.out: list[str] = []

    # ------------------------------------------------------------ primitives
    def tip(self, sid: str) -> str:
        r = self.s.get(sid)
        n = sid[1:]
        if not r:
            return f"Stream {n}"
        lines = [f"Stream {n} · {r['description']}",
                 f"{r['source']} → {r['target']}",
                 f"Total {_fmt(r['total_kg_per_kg_Ga'])} kg per kg Ga"]
        if r.get("Ga"):
            lines.append(f"Ga {_fmt(r['Ga'])} kg per kg Ga")
        return escape("\n".join(lines))

    def line(self, pts, arrow=True):
        d = "M" + " L".join(f"{x:.0f},{y:.0f}" for x, y in pts)
        end = ' marker-end="url(#ga-arrow)"' if arrow else ""
        self.out.append(f'<path d="{d}" fill="none" stroke="{INK}" stroke-width="1.5"{end}/>')

    def diamond(self, x, y, n):
        r = 12
        self.out.append(
            f'<path d="M{x},{y - r} L{x + r},{y} L{x},{y + r} L{x - r},{y} Z" '
            f'fill="#FFFFFF" stroke="{INK}" stroke-width="1.3"/>'
            f'<text x="{x}" y="{y + 3.5}" font-size="10.5" font-weight="600" '
            f'text-anchor="middle" fill="{INK}">{n}</text>')

    def label(self, x, y, text, anchor="start", waste=False, size=13):
        colour = WASTE if waste else INK
        self.out.append(f'<text x="{x}" y="{y}" font-size="{size}" font-style="italic" '
                        f'font-weight="700" text-anchor="{anchor}" fill="{colour}">'
                        f'{escape(text)}</text>')

    def stream(self, sid, pts, at, name=None, name_xy=None, anchor="start", waste=False,
               arrow=True):
        """A numbered stream: polyline, diamond at point ``at``, optional label."""
        self.out.append(f'<g class="ga-stream"><title>{self.tip(sid)}</title>')
        self.line(pts, arrow)
        self.diamond(*at, sid[1:])
        if name:
            self.label(*name_xy, name, anchor=anchor, waste=waste)
        self.out.append("</g>")

    def unit(self, up, cx, y, w=BW):
        x = cx - w / 2
        cut = 12
        rec = ""
        if self.meb is not None and getattr(self.meb, "recoveries", None):
            rec = f"\nGallium recovery {self.meb.recoveries.get(up, 0) * 100:.1f}%"
        self.out.append(
            f'<g class="ga-unit"><title>{up} · {NAMES[up]}{rec}</title>'
            f'<path d="M{x},{y} L{x + w - cut},{y} L{x + w},{y + cut} L{x + w},{y + BH} '
            f'L{x},{y + BH} Z" fill="#FFFFFF" stroke="{INK}" stroke-width="1.6"/>'
            f'<rect x="{x - 4}" y="{y - 11}" width="{14 + 7 * len(up)}" height="20" rx="4" '
            f'fill="{TAG}"/>'
            f'<text x="{x + 3}" y="{y + 3}" font-size="10.5" font-weight="700" '
            f'fill="#FFFFFF">{up}</text>'
            f'<text x="{cx}" y="{y + BH / 2 + 6}" font-size="15" font-weight="700" '
            f'text-anchor="middle" fill="{INK}">{escape(NAMES[up])}</text></g>')

    # ------------------------------------------------------------- the drawing
    def draw(self) -> str:
        o = self.out
        o.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
                 f'width="100%" role="img" aria-label="Gallium recovery process flow diagram" '
                 f'font-family="{FONT}">')
        o.append(f'<defs><marker id="ga-arrow" viewBox="0 0 10 10" refX="9" refY="5" '
                 f'markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
                 f'<path d="M0,0 L10,5 L0,10 Z" fill="{INK}"/></marker></defs>')
        o.append('<style>.ga-stream:hover path, .ga-unit:hover path{stroke-width:2.6}'
                 '.ga-stream, .ga-unit{cursor:help}</style>')

        top, bot = (lambda k: ROWS[k]), (lambda k: ROWS[k] + BH)
        mid = lambda k: ROWS[k] + BH / 2  # noqa: E731
        L, R = CX - BW / 2, CX + BW / 2

        # source and product
        sy = ROWS["SRC"]
        o.append(f'<g class="ga-unit"><title>Host alumina refinery (Bayer process)</title>'
                 f'<rect x="{CX - 125}" y="{sy}" width="250" height="76" fill="{SOURCE_FILL}" '
                 f'stroke="{INK}" stroke-width="1.6"/>'
                 f'<rect x="{CX - 129}" y="{sy - 11}" width="62" height="20" rx="4" fill="{TAG}"/>'
                 f'<text x="{CX - 122}" y="{sy + 3}" font-size="10.5" font-weight="700" '
                 f'fill="#FFFFFF">Source</text>'
                 f'<text x="{CX}" y="{sy + 44}" font-size="16" font-weight="700" '
                 f'text-anchor="middle" fill="{INK}">Alumina refinery</text></g>')
        py = ROWS["PRODUCT"]
        o.append(f'<g class="ga-unit"><title>4N gallium product, 1 kg basis</title>'
                 f'<rect x="{CX - 95}" y="{py}" width="190" height="56" rx="10" '
                 f'fill="{PRODUCT_FILL}" stroke="{INK}" stroke-width="1.6"/>'
                 f'<text x="{CX}" y="{py + 34}" font-size="16" font-weight="700" '
                 f'text-anchor="middle" fill="#FFFFFF">4N gallium</text></g>')

        # main spine
        spine = [("S1", sy + 76, "UP1"), ("S3", bot("UP1"), "UP2"), ("S5", bot("UP2"), "UP3"),
                 ("S8", bot("UP3"), "UP5"), ("S14", bot("UP5"), "UP7"),
                 ("S21", bot("UP7"), "UP8"), ("S23", bot("UP8"), "UP9"),
                 ("S28", bot("UP9"), "UP10"), ("S31", bot("UP10"), "UP11"),
                 ("S34", bot("UP11"), "PRODUCT")]
        for sid, y0, nxt in spine:
            y1 = top(nxt)
            self.stream(sid, [(CX, y0), (CX, y1)], (CX, (y0 + y1) / 2))

        # recycles to the refinery
        self.stream("S2", [(R, mid("UP1")), (700, mid("UP1")), (700, sy + 54), (CX + 125, sy + 54)],
                    (700, (mid("UP1") + sy + 54) / 2), "Filter residue", (R + 10, mid("UP1") - 8))
        self.stream("S4", [(R, mid("UP2")), (770, mid("UP2")), (770, sy + 22), (CX + 125, sy + 22)],
                    (770, (mid("UP2") + sy + 22) / 2), "Ga-depleted liquor", (R + 10, mid("UP2") - 8))

        # UP3 washing
        y = mid("UP3")
        self.stream("S6", [(250, y), (L, y)], (322, y), "Water", (240, y + 5), anchor="end")
        self.stream("S7", [(R, y), (750, y)], (678, y), "Wash waste", (760, y + 5))

        # UP4 / UP5 / UP6 row
        y = mid("UP5")
        u4l, u4r = UP4_CX - SIDE_W / 2, UP4_CX + SIDE_W / 2
        u6l = UP6_CX - SIDE_W / 2
        self.stream("S13", [(u4r, y), (L, y)], ((u4r + L) / 2, y), "4% H₂SO₄",
                    ((u4r + L) / 2, y + 30), anchor="middle")
        self.stream("S15", [(R, y), (u6l, y)], ((R + u6l) / 2, y))
        self.stream("S10", [(20, y), (u4l, y)], (75, y), "Water", (20, y - 14))
        t4, b4 = top("UP4"), bot("UP4")
        self.stream("S9", [(UP4_CX, b4 + 70), (UP4_CX, b4)], (UP4_CX, b4 + 34),
                    "98% H₂SO₄", (UP4_CX, b4 + 90), anchor="middle")
        self.stream("S11", [(UP4_CX - 45, t4), (UP4_CX - 45, t4 - 70)], (UP4_CX - 45, t4 - 34),
                    "Salty water", (UP4_CX - 45, t4 - 78), anchor="middle", waste=True)
        self.stream("S12", [(UP4_CX + 45, t4), (UP4_CX + 45, t4 - 70)], (UP4_CX + 45, t4 - 34),
                    "Acid mist", (UP4_CX + 45, t4 - 78), anchor="middle", waste=True)
        t6, b6 = top("UP6"), bot("UP6")
        self.stream("S16", [(UP6_CX - 45, t6 - 70), (UP6_CX - 45, t6)], (UP6_CX - 45, t6 - 34),
                    "Water", (UP6_CX - 45, t6 - 78), anchor="middle")
        self.stream("S17", [(UP6_CX + 45, t6 - 70), (UP6_CX + 45, t6)], (UP6_CX + 45, t6 - 34),
                    "Resin", (UP6_CX + 45, t6 - 78), anchor="middle")
        self.stream("S18", [(UP6_CX - 45, b6), (UP6_CX - 45, b6 + 70)], (UP6_CX - 45, b6 + 34),
                    "Wastewater", (UP6_CX - 45, b6 + 90), anchor="middle", waste=True)
        self.stream("S19", [(UP6_CX + 45, b6), (UP6_CX + 45, b6 + 70)], (UP6_CX + 45, b6 + 34),
                    "Waste resin", (UP6_CX + 45, b6 + 90), anchor="middle", waste=True)

        # lower train
        y = mid("UP7")
        self.stream("S20", [(250, y), (L, y)], (322, y), "32% NaOH", (240, y + 5), anchor="end")
        y = mid("UP8")
        self.stream("S22", [(R, y), (750, y)], (678, y), "Centrifuge solution", (760, y + 5))
        ya, yb = top("UP9") + 17, top("UP9") + 40
        self.stream("S24", [(250, ya), (L, ya)], (322, ya), "32% NaOH", (240, ya + 5), anchor="end")
        self.stream("S25", [(250, yb), (L, yb)], (322, yb), "CaO", (240, yb + 5), anchor="end")
        self.stream("S26", [(R, ya), (750, ya)], (678, ya), "Condensate waste", (760, ya + 5),
                    waste=True)
        self.stream("S27", [(R, yb), (750, yb)], (678, yb), "Filter cake", (760, yb + 5),
                    waste=True)
        ya, yb = top("UP10") + 17, top("UP10") + 40
        self.stream("S29", [(R, ya), (750, ya)], (678, ya), "Electrolytic gas", (760, ya + 5),
                    waste=True)
        self.stream("S30", [(R, yb), (750, yb)], (678, yb), "Electrolytic effluent",
                    (760, yb + 5), waste=True)
        y = mid("UP11")
        self.stream("S32", [(250, y), (L, y)], (322, y), "HCl", (240, y + 5), anchor="end")
        self.stream("S33", [(R, y), (750, y)], (678, y), "Refining effluent", (760, y + 5),
                    waste=True)

        # units last so they sit above line ends
        for up in ("UP1", "UP2", "UP3", "UP5", "UP7", "UP8", "UP9", "UP10", "UP11"):
            self.unit(up, CX, ROWS[up])
        self.unit("UP4", UP4_CX, ROWS["UP4"], SIDE_W)
        self.unit("UP6", UP6_CX, ROWS["UP6"], SIDE_W)

        o.append("</svg>")
        return "".join(o)


def svg(streams: dict | None = None, meb=None) -> str:
    """Standalone SVG of the flowsheet. Tooltips carry live values when given."""
    return _Pen(streams, meb).draw()


# Diagram number for each register stream, for the stream table.
def number(sid: str) -> str:
    return sid[1:]
