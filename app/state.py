"""
Session state for the multipage app: the inputs a user has edited, the method
choices, and the snapshot taken when they press Run.

Results are always calculated from the Run snapshot, never from inputs typed
since, so every results panel matches the run it says it is from. The model
runs in about a millisecond, so nothing is cached: the snapshot is re-run on
each page view.
"""

from __future__ import annotations

import dataclasses
from datetime import datetime

import streamlit as st

from openga_v1 import config, engine
from openga_v1.config import (UNIT_OPS, CAPEX_MODES, CATEGORIES, ENERGY_MODES, PERCENT_KEYS,
                              POLICY_MODELS, RESIN_PRESETS, SELECTOR_KEYS, ModelInputs,
                              base_params, meta)


# Inputs replaced by a method selector, so editing them here would do nothing.
HIDDEN = {"POLSEL"}
# Ion exchange inputs that a named resin preset overrides.
RESIN_KEYS = {"IXRec", "CoAdsV", "CoAdsAl", "ResinCap"}
CUSTOM_RESIN = 4

SECTION_NOTES = {
    ("Plant basis", "Capacity, hours and life"):
        "How much gallium the plant makes, how many hours a year it runs and for how long.",
    ("Plant basis", "Feed liquor chemistry"):
        "What is in the spent Bayer liquor. The gallium assay is the largest unknown in the model.",
    ("Process", "Recovery cascade, UP1 to UP11"):
        "The share of gallium each unit operation passes on. Overall recovery is their product.",
    ("Process", "Ion exchange performance"):
        "Resin recovery, co-adsorption and capacity. Editable only with the Custom resin preset.",
    ("Process", "Reagent doses and strengths"):
        "Wash, eluant and regeneration volumes, and the caustic, lime and acid doses.",
    ("Process", "Electrowinning and electrolyte"):
        "Electrolyte composition, cell voltage and current efficiency, which set electrowinning power.",
    ("Process", "Energy and duty"):
        "Pump heads and efficiencies, evaporation and the ancillary power allowance.",
    ("Equipment", "Sizing parameters"):
        "Design velocities, residence times and capacities that turn flows into equipment sizes.",
    ("Equipment", "Costing allowances"):
        "Vessel construction allowances, spares and directly priced items.",
    ("Capital", "Escalation, location and currency"):
        "Brings 2010 US Gulf Coast cost correlations to current Australian dollars.",
    ("Capital", "Installation and factorial build-up"):
        "Installation factors and the steps from installed equipment to fixed capital, "
        "including the equipment-list completeness factor.",
    ("Capital", "Comparable plant (six-tenths mode)"):
        "The published plant used as the capital benchmark.",
    ("Operating cost", "Unit prices"):
        "Prices for electricity, steam, reagents, resin, water and waste disposal.",
    ("Operating cost", "Fixed cost"):
        "Labour, maintenance, insurance and plant overhead.",
    ("Finance", "Tax, inflation and salvage"):
        "Company tax, the inflation used to deflate tax depreciation, and end-of-life value.",
    ("Finance", "Cost of capital"):
        "The CAPM build-up that sets the real weighted average cost of capital (WACC).",
    ("Finance", "Concessional debt"):
        "Terms for supported debt under the policy packages.",
    ("Policy", "CMPTI"):
        "Critical Minerals Production Tax Incentive: rate, claim years and timing.",
    ("Policy", "Capital grant"):
        "When a capital grant is received and how it is taxed.",
    ("Policy", "Offtake assessment"):
        "Contract terms for testing an offtake against the LCOP. They do not change the LCOP.",
    ("Energy mix", "Delivered shares"):
        "Share of delivered electricity from each source. The five shares must sum to 100%.",
    ("Energy mix", "Route prices"):
        "Delivered price of each electricity source other than the grid.",
    ("Energy mix", "Battery storage"):
        "Round-trip efficiency, cost, life and manufacturing emissions of battery storage.",
    ("Energy mix", "Financial connection"):
        "Whether the blended electricity price replaces the base price in the cost model.",
    ("Carbon", "Electricity and fuel factors"):
        "Emission factors for grid electricity and natural gas.",
    ("Carbon", "Renewable and battery embodied factors"):
        "Manufacturing emissions of solar and wind generation, per kWh delivered.",
    ("Carbon", "Embodied chemical and waste factors"):
        "Upstream emissions of purchased reagents, resin, water and waste treatment.",
    ("Carbon", "Allocation"):
        "How liquor-circuit pumping is split between unit operations.",
}


# --------------------------------------------------------------------------
# state
# --------------------------------------------------------------------------
def init() -> None:
    ss = st.session_state
    ss.setdefault("overrides", {})
    ss.setdefault("cfg", config.ModelConfig())
    ss.setdefault("run", None)


def current_inputs() -> ModelInputs:
    p = dict(base_params())
    p.update(st.session_state.overrides)
    return ModelInputs(params=p, cfg=st.session_state.cfg)


def run_now() -> None:
    st.session_state.run = {"overrides": dict(st.session_state.overrides),
                            "cfg": st.session_state.cfg,
                            "at": datetime.now().strftime("%H:%M")}
    st.session_state.pop("mc", None)
    st.session_state.pop("mc_done", None)


def has_run() -> bool:
    return st.session_state.get("run") is not None


def is_stale() -> bool:
    r = st.session_state.get("run")
    return bool(r) and (r["overrides"] != st.session_state.overrides
                        or r["cfg"] != st.session_state.cfg)


def run_inputs() -> ModelInputs:
    r = st.session_state.run
    p = dict(base_params())
    p.update(r["overrides"])
    return ModelInputs(params=p, cfg=r["cfg"])


def results():
    return engine.run(run_inputs())


def reset_all() -> None:
    st.session_state.overrides = {}
    st.session_state.cfg = config.ModelConfig()
    for name in list(st.session_state):
        if name.startswith(("in_", "cfg_", "cx_", "stage_")):
            del st.session_state[name]


def n_edited() -> int:
    return len(st.session_state.overrides)


# --------------------------------------------------------------------------
# run controls
# --------------------------------------------------------------------------
def run_button(where: str, label: str = "Run model", stretch: bool = False) -> None:
    st.button(label, type="primary", key=f"run_{where}", on_click=run_now,
              icon=":material/play_arrow:", width="stretch" if stretch else "content")


def run_footer(where: str) -> None:
    """Run button at the foot of each step, with a one-line status."""
    st.write("")
    c = st.columns([1, 5], vertical_alignment="center")
    with c[0]:
        run_button(where)
    with c[1]:
        if not has_run():
            st.caption("Runs the whole model on every input across all five steps.")
        elif is_stale():
            st.caption("Inputs have changed since the last run.")
        else:
            st.caption(f"Results are up to date (run at {st.session_state.run['at']}).")


def results_container():
    """Container for anything calculated. Returns None before the first run."""
    if not has_run():
        return None
    if is_stale():
        st.warning("Inputs have changed since the last run. These results are from the "
                   "previous run: press **Run model** to update them.",
                   icon=":material/update:")
        return st.container(key="stale_results")
    return st.container(key="fresh_results")


# --------------------------------------------------------------------------
# inputs
# --------------------------------------------------------------------------
def _apply_input(parameter, widget_key, percent=False):
    shown = st.session_state[widget_key]
    value = float(shown) / 100 if percent else float(shown)
    if abs(value - meta(parameter)["default"]) > 1e-15:
        st.session_state.overrides[parameter] = value
    else:
        st.session_state.overrides.pop(parameter, None)
    for group, title, keys in CATEGORIES:
        if parameter in keys:
            other = f"in_{group}_{title}_{parameter}"
            if other != widget_key and other in st.session_state:
                st.session_state[other] = shown


def _label(m: dict, key: str, pct: bool) -> str:
    unit = "%" if pct else m["unit"]
    unit = "" if unit in ("-", "", None) else f" ({unit})"
    status = (m.get("status") or "").upper()
    tag = ""
    if status.startswith("PLACEHOLDER"):
        tag = " :orange-badge[Placeholder]"
    elif status.startswith("ASSUMPTION"):
        tag = " :gray-badge[Assumption]"
    elif status.startswith(("CITED", "STATUTORY")):
        tag = " :green-badge[Cited]"
    if key in st.session_state.overrides:
        tag += " :blue-badge[Edited]"
    return f"{m['label']}{unit}{tag}"


def _help(m: dict, key: str) -> str:
    return (f"**{m.get('status', '')}** · confidence {m.get('conf', '-')}\n\n"
            f"{m.get('source', '')}\n\nModel key: `{key}` · published default: "
            f"{m.get('default')}")


def input_sections(sections: list[tuple[str, str]], start: int = 1) -> int:
    """Numbered expanders of inputs, two per row. Returns the next number."""
    mi = current_inputs()
    custom_resin = st.session_state.cfg.resin_preset == CUSTOM_RESIN
    n = start
    for group, title in sections:
        keys = next(k for g, t, k in CATEGORIES if g == group and t == title)
        keys = [k for k in keys if k not in HIDDEN and "default" in meta(k)]
        if not keys:
            continue
        with st.expander(f"{n}. {title}"):
            note = SECTION_NOTES.get((group, title))
            if note:
                st.caption(note)
            cols = st.columns(2)
            for i, key in enumerate(keys):
                m = meta(key)
                pct = key in PERCENT_KEYS
                wkey = f"in_{group}_{title}_{key}"
                cur = mi.resolved().get(key, m["default"]) if key in RESIN_KEYS \
                    else mi.params.get(key, m["default"])
                locked = key in RESIN_KEYS and not custom_resin
                with cols[i % 2]:
                    if key in SELECTOR_KEYS:
                        opts = SELECTOR_KEYS[key]
                        if wkey not in st.session_state:
                            st.session_state[wkey] = int(cur) if int(cur) in opts else opts[0]
                        st.selectbox(_label(m, key, False), opts, key=wkey,
                                     help=_help(m, key),
                                     on_change=_apply_input, args=(key, wkey, False))
                    else:
                        shown = cur * 100 if pct else cur
                        if wkey not in st.session_state or locked:
                            st.session_state[wkey] = float(shown)
                        st.number_input(_label(m, key, pct), step=0.01, key=wkey,
                                        format="%.6g", disabled=locked,
                                        help=(_help(m, key) + ("\n\nSet by the resin preset. "
                                              "Choose **Custom** to edit." if locked else "")),
                                        on_change=_apply_input, args=(key, wkey, pct))
        n += 1
    return n


# --------------------------------------------------------------------------
# method choices (stored on the config, not as parameters)
# --------------------------------------------------------------------------
def _set_cfg(field: str, wkey: str) -> None:
    st.session_state.cfg = dataclasses.replace(st.session_state.cfg,
                                               **{field: st.session_state[wkey]})


def cfg_select(field: str, label: str, options: list, fmt, help: str = "") -> None:
    wkey = f"cfg_{field}"
    if wkey not in st.session_state:
        st.session_state[wkey] = getattr(st.session_state.cfg, field)
    st.selectbox(label, options, key=wkey, format_func=fmt, help=help or None,
                 on_change=_set_cfg, args=(field, wkey))


def resin_select() -> None:
    cfg_select("resin_preset", "Resin preset", [r.id for r in RESIN_PRESETS],
               lambda i: config.get_resin_preset(i).name,
               "One choice sets ion exchange recovery, co-adsorption and capacity together, "
               "because changing one alone describes no real resin. Choose Custom to edit them.")


def energy_select() -> None:
    cfg_select("energy_mode", "Energy model", list(ENERGY_MODES),
               lambda k: ENERGY_MODES[k].split(" — ")[0],
               "\n\n".join(f"**{k}** — {v}" for k, v in ENERGY_MODES.items()))


def capex_select() -> None:
    cfg_select("capex_mode", "Capital cost method", list(CAPEX_MODES),
               lambda k: CAPEX_MODES[k].split(" — ")[0],
               "\n\n".join(f"**{k}** — {v}" for k, v in CAPEX_MODES.items()))


def _apply_capex_user() -> None:
    u = st.session_state.cfg.capex_user
    st.session_state.cfg = dataclasses.replace(
        st.session_state.cfg,
        capex_user=config.CapexUserTotal(float(st.session_state.cx_fci),
                                         float(st.session_state.cx_cap),
                                         float(st.session_state.cx_exp), u.note))


def _apply_capex_stage() -> None:
    vals = {u: float(st.session_state.get(f"stage_{u}", 0.0)) for u, _ in UNIT_OPS}
    st.session_state.cfg = dataclasses.replace(st.session_state.cfg,
                                               capex_stage=config.CapexPerStage(vals))


def capex_entries() -> None:
    """Extra inputs for the two capital methods that take the user's own numbers."""
    cfg = st.session_state.cfg
    if cfg.capex_mode == "user_total":
        u = cfg.capex_user
        for k, v in (("cx_fci", u.fci_aud), ("cx_cap", u.capacity_t_yr),
                     ("cx_exp", u.scaling_exponent)):
            if k not in st.session_state:
                st.session_state[k] = float(v)
        c = st.columns(3)
        c[0].number_input("Your fixed capital investment (A$)", step=1e6, format="%.0f",
                          key="cx_fci", on_change=_apply_capex_user)
        c[1].number_input("Capacity that estimate is for (t Ga/yr)", step=1.0, key="cx_cap",
                          on_change=_apply_capex_user)
        c[2].number_input("Scaling exponent", step=0.05, format="%.2f", key="cx_exp",
                          on_change=_apply_capex_user)
        st.caption("Scaled to the model capacity on the stated exponent, then divided back "
                   "through the OSBL, engineering and contingency chain so those factors "
                   "are not applied on top of a number that already contains them.")
    elif cfg.capex_mode == "per_stage":
        vals = dict(cfg.capex_stage.values)
        st.caption("Installed cost of each unit operation: delivered, erected and connected. "
                   "These eleven numbers sum to ISBL; OSBL, engineering and contingency "
                   "apply on top.")
        cols = st.columns(3)
        for i, (u, nm) in enumerate(UNIT_OPS):
            if f"stage_{u}" not in st.session_state:
                st.session_state[f"stage_{u}"] = float(vals.get(u, 0.0))
            with cols[i % 3]:
                vals[u] = st.number_input(f"{u} · {nm} (A$)", step=1e6, format="%.0f",
                                          key=f"stage_{u}", on_change=_apply_capex_stage)
        total = sum(vals.values())
        st.caption(f"ISBL from your entries: A${total / 1e6:,.1f}M.")
        if total == 0:
            st.error("Every stage is zero, so all capital-derived figures will be zero.")


def policy_model_select() -> None:
    cfg_select("policy_model", "Policy model", list(POLICY_MODELS),
               lambda k: POLICY_MODELS[k].split(" — ")[0],
               "\n\n".join(f"**{k}** — {v}" for k, v in POLICY_MODELS.items()))


def package_select() -> None:
    if st.session_state.cfg.policy_model == "v31":
        pkgs = config.default_policy_packages(base_params())
        cfg_select("policy_package", "Policy package used for results",
                   [k.id for k in pkgs], lambda i: next(k.name for k in pkgs if k.id == i),
                   "The results summary leads with this package and lists the others "
                   "beside it.")
    else:
        cfg_select("legacy_policy", "Policy scenario used for results",
                   [s.id for s in config.LEGACY_POLICY_SCENARIOS],
                   lambda i: next(s.name for s in config.LEGACY_POLICY_SCENARIOS if s.id == i))


def package_name(of_run: bool = True) -> str:
    cfg = st.session_state.run["cfg"] if (of_run and has_run()) else st.session_state.cfg
    if cfg.policy_model == "v31":
        pkgs = config.default_policy_packages(base_params())
        return next(k.name for k in pkgs if k.id == cfg.policy_package)
    return next(s.name for s in config.LEGACY_POLICY_SCENARIOS if s.id == cfg.legacy_policy)


def fmt_aud(x: float, nd: int = 0) -> str:
    return f"A${x:,.{nd}f}"


def section_title(n: int, text: str) -> None:
    st.markdown(f"##### {n}. {text}")


