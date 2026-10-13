"""
Presentation helpers shared by every OpenGa page.

Styling follows the UNSW open-access copper value-chain tool so the two
models read as one family: the UNSW logo header with a yellow rule, callout
boxes, card-style expanders and a footer on every page. Nothing here touches
the model.
"""

from __future__ import annotations

import base64
from pathlib import Path

import streamlit as st

ASSETS = Path(__file__).resolve().parent / "assets"

BRAND_BLUE = "#002664"
BRAND_YELLOW = "#FFCD00"
SOFT_BLUE = "#EEF4FB"
TEXT = "#172033"
MUTED = "#5A6577"
LINE = "#D8E2EF"

PRODUCT = "OpenGa"
VERSION = "V2"
HEADER_LABEL = "Gallium Recovery Assessment<br>Open-Access Research Model"


def apply_style() -> None:
    st.markdown(f"""
<style>
.stApp {{ background: #F5F7F5; color: {TEXT}; }}
[data-testid="stMainBlockContainer"], .block-container {{
    max-width: 1180px; padding-top: 3.2rem; padding-bottom: 3rem;
}}
h1, h2, h3, h4 {{ color: {BRAND_BLUE}; letter-spacing: -0.01em; }}
div[data-testid="stMetric"] {{
    background: #FFFFFF; border: 1px solid {LINE}; border-radius: 12px;
    padding: 0.8rem 1rem; box-shadow: 0 2px 8px rgba(0, 38, 100, 0.05);
}}
div[data-testid="stExpander"] {{
    border: 1px solid {LINE}; border-radius: 12px; overflow: hidden;
    margin-bottom: 0.6rem; background: #FFFFFF;
}}
div[data-testid="stExpander"] summary {{
    font-weight: 700; color: {BRAND_BLUE}; background: #F8FAFD;
}}
div[data-testid="stExpander"] summary p {{ font-weight: 700; font-size: 0.95rem; }}
.stButton > button, .stDownloadButton > button {{ border-radius: 10px; font-weight: 700; }}
.ga-callout {{
    background: {SOFT_BLUE}; border-left: 5px solid {BRAND_YELLOW}; border-radius: 10px;
    padding: 0.9rem 1rem; margin: 0.35rem 0 1rem 0; color: {TEXT}; line-height: 1.5;
}}
.ga-kicker {{ color: {MUTED}; font-size: 1rem; margin-top: -0.4rem; }}
.ga-chip {{
    display: inline-block; background: {SOFT_BLUE}; color: {BRAND_BLUE};
    border: 1px solid {LINE}; border-radius: 999px; padding: 0.22rem 0.65rem;
    margin: 0.1rem 0.25rem 0.1rem 0; font-size: 0.8rem; font-weight: 700;
    letter-spacing: 0.03em;
}}
.ga-flow-wrap {{ overflow-x: auto; padding: 0.4rem 0 0.8rem 0; }}
.ga-flow {{ display: flex; align-items: stretch; min-width: 860px; gap: 6px; }}
.ga-node {{
    flex: 1; border: 1px solid #CAD8E8; background: #FFFFFF; border-radius: 12px;
    padding: 0.9rem; min-height: 120px; box-shadow: 0 2px 8px rgba(0, 38, 100, 0.05);
}}
.ga-node strong {{ color: {BRAND_BLUE}; display: block; margin-bottom: 0.15rem; line-height: 1.3; }}
.ga-node em {{ display: block; font-style: normal; color: {BRAND_BLUE}; opacity: 0.7;
              font-size: 0.75rem; font-weight: 700; letter-spacing: 0.04em; margin-bottom: 0.35rem; }}
.ga-node span {{ color: {MUTED}; font-size: 0.87rem; line-height: 1.4; }}
.ga-arrow {{ display: flex; align-items: center; color: {BRAND_BLUE};
            font-size: 1.1rem; font-weight: 700; }}
.ga-total {{ border: 2px solid {BRAND_YELLOW}; background: #FFFDF2; }}
.ga-cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
            gap: 10px; margin: 0.3rem 0 1rem 0; }}
.ga-card {{ background: #FFFFFF; border: 1px solid {LINE}; border-radius: 12px;
           padding: 0.85rem 1rem; }}
.ga-card strong {{ color: {BRAND_BLUE}; display: block; margin-bottom: 0.25rem; }}
.ga-card span {{ color: {MUTED}; font-size: 0.9rem; line-height: 1.45; }}
.ga-hero {{ background: #FFFFFF; border: 1px solid {LINE}; border-radius: 14px;
           padding: 1.1rem 1.2rem; box-shadow: 0 2px 8px rgba(0, 38, 100, 0.05); height: 100%; }}
.ga-hero .lab {{ color: {MUTED}; font-size: 0.9rem; font-weight: 600; }}
.ga-hero .val {{ color: {BRAND_BLUE}; font-size: 2.6rem; font-weight: 800; line-height: 1.15;
                margin: 0.2rem 0; }}
.ga-hero .val small {{ font-size: 1rem; font-weight: 600; color: {MUTED}; }}
.ga-hero .sub {{ color: {MUTED}; font-size: 0.88rem; line-height: 1.45; }}
.ga-strip {{ display: flex; flex-wrap: wrap; gap: 0.4rem 1.6rem; color: {MUTED};
            font-size: 0.93rem; margin: 0.6rem 0 1.2rem 0; }}
.ga-strip b {{ color: {TEXT}; }}
.ga-strip-title {{ color: {BRAND_BLUE}; font-size: 0.78rem; font-weight: 700;
                  letter-spacing: 0.05em; text-transform: uppercase; margin-top: 1rem; }}
.ga-strip {{ margin-top: 0.25rem; }}
.ga-empty {{ background: #FFFFFF; border: 1px dashed #B9C8DA; border-radius: 12px;
            padding: 1.4rem 1.2rem; color: {MUTED}; text-align: center; margin: 0.6rem 0; }}
.ga-empty strong {{ color: {BRAND_BLUE}; display: block; font-size: 1.05rem; margin-bottom: 0.2rem; }}
.ga-badge {{ display: inline-block; border-radius: 6px; padding: 0.05rem 0.4rem;
            font-size: 0.7rem; font-weight: 700; letter-spacing: 0.03em; margin-left: 0.35rem;
            border: 1px solid; vertical-align: middle; }}
.ga-b-cited {{ color: #1d5f3a; border-color: #b9dcc7; background: #eef8f2; }}
.ga-b-assume {{ color: #23466f; border-color: #c6d6ea; background: #f1f6fc; }}
.ga-b-place {{ color: #7a4a00; border-color: #f0d49a; background: #fff7e6; }}
.ga-b-other {{ color: {MUTED}; border-color: {LINE}; background: #f7f8fa; }}
.ga-edited {{ color: {BRAND_BLUE}; font-size: 0.75rem; font-weight: 700; margin-left: 0.35rem; }}
.st-key-stale_results {{ opacity: 0.55; }}
div[class*="st-key-card_"] {{
    background: #FFFFFF; border-color: {LINE} !important; border-radius: 12px;
    box-shadow: 0 2px 8px rgba(0, 38, 100, 0.05);
}}
.ga-read {{ color: {MUTED}; font-size: 0.86rem; line-height: 1.45; margin: 0.2rem 0 1rem 0; }}
.ga-read b {{ color: {TEXT}; }}
.ga-pfd {{ max-width: 760px; margin: 0.4rem auto 0.6rem auto; }}
.ga-pfd svg {{ width: 100%; height: auto; display: block; }}
.ga-sidebrand {{ color: {BRAND_BLUE}; font-weight: 800; font-size: 1.15rem; line-height: 1.2; }}
.ga-sidebrand span {{ display: block; color: {MUTED}; font-weight: 500; font-size: 0.8rem; }}
.unsw-brand-header {{
    display: flex; align-items: center; justify-content: space-between; gap: 1rem;
    border-bottom: 4px solid {BRAND_YELLOW}; padding: 0 0 0.8rem 0; margin: 0 0 1.2rem 0;
}}
.unsw-brand-logo {{ width: 190px; max-width: 42vw; height: auto; display: block; }}
.unsw-brand-label {{ color: {BRAND_BLUE}; font-size: 0.82rem; font-weight: 700;
                    letter-spacing: 0.045em; text-transform: uppercase; text-align: right; }}
.unsw-footer {{ border-top: 1px solid {LINE}; margin-top: 2.4rem; padding-top: 0.9rem;
               color: {MUTED}; font-size: 0.82rem; text-align: center; }}
@media (max-width: 640px) {{
    .unsw-brand-logo {{ width: 150px; }}
    .unsw-brand-label {{ font-size: 0.72rem; max-width: 44%; }}
    .ga-hero .val {{ font-size: 2rem; }}
}}
</style>""", unsafe_allow_html=True)


def _logo_uri() -> str:
    try:
        data = (ASSETS / "unsw_logo.png").read_bytes()
        return "data:image/png;base64," + base64.b64encode(data).decode("ascii")
    except OSError:
        return ""


def header() -> None:
    uri = _logo_uri()
    logo = (f'<img class="unsw-brand-logo" src="{uri}" alt="UNSW Sydney logo">' if uri
            else '<div style="font-size:2rem;font-weight:800;color:#111;">UNSW</div>')
    st.markdown(f'<div class="unsw-brand-header">{logo}'
                f'<div class="unsw-brand-label">{HEADER_LABEL}</div></div>',
                unsafe_allow_html=True)


def footer() -> None:
    st.markdown(f'<div class="unsw-footer">{PRODUCT} {VERSION} · © UNSW Sydney 2026.</div>',
                unsafe_allow_html=True)


def callout(title: str, body: str, extra: str = "") -> None:
    tail = f"<br><span style='color:{MUTED};'>{extra}</span>" if extra else ""
    st.markdown(f"<div class='ga-callout'><strong>{title}</strong><br>{body}{tail}</div>",
                unsafe_allow_html=True)


def step_intro(title: str, does: str, outputs: str) -> None:
    """Page title and the 'What this page does' box used on every step."""
    header()
    st.title(title)
    callout("What this page does", does, f"<strong>Primary outputs:</strong> {outputs}")


def how_to(steps: list[str], outputs: list[str] | None = None, notes: str = "") -> None:
    with st.expander("How to use this page"):
        md = "**Recommended workflow**\n\n" + "\n".join(f"{i}. {s}" for i, s in enumerate(steps, 1))
        if outputs:
            md += "\n\n**What you get after pressing Run**\n\n" + "\n".join(f"- {o}" for o in outputs)
        if notes:
            md += "\n\n" + notes
        st.markdown(md)


def empty_state(text: str = "Press **Run model** to calculate results for the current inputs.") -> None:
    st.markdown(f"<div class='ga-empty'><strong>No results yet</strong>{md_inline(text)}</div>",
                unsafe_allow_html=True)


def md_inline(text: str) -> str:
    """Bold markers to HTML for use inside raw HTML blocks."""
    out, bold = "", False
    for part in text.split("**"):
        out += (f"<b>{part}</b>" if bold else part)
        bold = not bold
    return out


def hero(label: str, value: str, unit: str, sub: str = "") -> str:
    return (f"<div class='ga-hero'><div class='lab'>{label}</div>"
            f"<div class='val'>{value} <small>{unit}</small></div>"
            f"<div class='sub'>{sub}</div></div>")


def table(df, fmt_map: dict | None = None, **kw) -> None:
    st.dataframe(df.style.format(fmt_map or {}), width="stretch", hide_index=True, **kw)


def strip(items: list[tuple[str, str]], title: str = "") -> None:
    """One quiet line of secondary figures: [(label, value), ...]."""
    head = f"<div class='ga-strip-title'>{title}</div>" if title else ""
    st.markdown(head + "<div class='ga-strip'>" + "".join(
        f"<div>{lab} <b>{val}</b></div>" for lab, val in items) + "</div>",
        unsafe_allow_html=True)


def chart(ch, name: str, read: str = "") -> None:
    """A chart in a white card, with a 'How to read this' line under it."""
    with st.container(key=f"card_{name}", border=True):
        st.altair_chart(ch, width="stretch")
        if read:
            st.markdown(f"<div class='ga-read'><b>How to read this.</b> {md_inline(read)}</div>",
                        unsafe_allow_html=True)


def flow(nodes: list[tuple[str, str, str]], total: tuple[str, str]) -> None:
    """Process-flow cards: [(title, tag, body), ...] then a highlighted total card."""
    parts = []
    for i, (title, tag, body) in enumerate(nodes):
        if i:
            parts.append("<div class='ga-arrow'>→</div>")
        parts.append(f"<div class='ga-node'><strong>{title}</strong><em>{tag}</em>"
                     f"<span>{body}</span></div>")
    parts.append("<div class='ga-arrow'>→</div>")
    parts.append(f"<div class='ga-node ga-total'><strong>{total[0]}</strong><em>RESULT</em>"
                 f"<span>{total[1]}</span></div>")
    st.markdown("<div class='ga-flow-wrap'><div class='ga-flow'>" + "".join(parts)
                + "</div></div>", unsafe_allow_html=True)


def cards(items: list[tuple[str, str]]) -> None:
    st.markdown("<div class='ga-cards'>" + "".join(
        f"<div class='ga-card'><strong>{t}</strong><span>{b}</span></div>" for t, b in items)
        + "</div>", unsafe_allow_html=True)


def badge(status: str) -> str:
    s = (status or "").upper()
    cls = ("ga-b-cited" if s.startswith(("CITED", "STATUTORY")) else
           "ga-b-place" if s.startswith("PLACEHOLDER") else
           "ga-b-assume" if s.startswith(("ASSUMPTION", "ESTIMATE")) else "ga-b-other")
    return f"<span class='ga-badge {cls}'>{s.title() if s else '—'}</span>"


def esc_dollars(text: str) -> str:
    """Streamlit markdown reads paired $ signs as maths."""
    return text.replace("$", "\\$")
