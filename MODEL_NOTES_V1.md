# OpenGa — interface

Techno-economic and carbon model for primary gallium recovery from an Australian
Bayer liquor slipstream, with a tabbed Streamlit front end.

```bash
./run.sh                                  # installs deps and starts the app
# or
pip install -r requirements.txt
streamlit run app/streamlit_app.py

python3 selftest.py                       # headline numbers + checks, no browser
```

---

## Read this first: two models, not two versions

This app carries **two engines**, and they disagree about the same plant.

| | v3.3 mechanistic (default) | Legacy WP3/WP4 |
|---|---|---|
| Electricity | computed from duty | Luo's allocation, scaled |
| Capital | 16 items sized off the MEB | scaled on gallium capacity |
| Production cost | A$697.40/kg | A$832.69/kg *(from the WP4 workbook)* |
| p* | A$836.67/kg | A$934.85/kg *(from the WP4 workbook)* |

The split is that WP3 takes electricity from Luo et al.'s per-unit allocation scaled
by throughput, resin and hardness ratios, while v3.0 recomputes it as ρgQH/η for
pumping and Faraday for electrowinning. Luo's 143.6 kWh/kg cannot be reconciled with a
pumping calculation at any plausible head — you would need about 460 m. Capital splits
for the same reason: WP4's estimate never sees liquor throughput, so doubling the feed
volume leaves it unchanged.

**The default is v3.3 mechanistic**, because every number in it traces to a calculation
rather than a scaled allocation.

**One caveat on legacy mode, stated plainly.** It reinstates WP3's *energy allocation*
on top of the v3.3 physical basis. It does **not** restore WP3's six-stage recovery
cascade, so it lands near the old figures without reproducing them — about 140.3 kWh/kg
at the old 103 mg/L assay, against WP3's 143.558. If you need the original numbers to
the decimal, quote them from the WP3/WP4 workbooks, not from here. The Checks tab
reports the comparison as a documented divergence, never as a passing test.

---

## Modes

**Baseline** runs the shipped v3.3 defaults and ignores every edit. Inputs are shown
read-only so you can still read the sources on stage.

**User** unlocks every input. Edits are held in session state and listed at the foot of
the Inputs tab; one button resets them all.

The **structural switches** in the sidebar stay live in both modes, because they change
which equations run rather than what goes into them:

- **Energy model** — mechanistic or legacy WP3
- **CAPEX method** — four options, below
- **Policy model** — the v3.1 module or the legacy WP4 three scenarios
- **Resin preset** — four presets driving recovery, co-adsorption and capacity together
- **Policy package / scenario**

---

## The four CAPEX methods

1. **Bottom-up** — sixteen items sized from the MEB and costed with Towler & Sinnott
   Table 7.2 correlations, escalated on CEPCI, converted at the location factor and FX,
   then multiplied by a visible equipment-list **completeness factor**. That factor
   exists because the itemised list covers major process equipment only and costs out at
   roughly one sixth of the published comparable. Showing the gap is better than burying
   it in a fudged correlation.
2. **Six-tenths scaling** — a comparable plant's capital scaled on gallium capacity.
3. **User total** — your own FCI and the capacity it belongs to, scaled to the model
   capacity on a stated exponent.
4. **Per stage** — eleven **installed** costs, one per unit operation, summing to ISBL.
   Installed means delivered, erected and connected. OSBL, engineering and contingency
   apply on top to reach FCI. These are not bare equipment costs and not shares of FCI.

Modes 2, 3 and 4 all land on ISBL, so the factorial build-up to FCI is shared and the
comparison is like for like. Modes 2 and 3 divide their input back through the
OSBL/engineering/contingency chain first, so those factors are not applied twice to a
number that already contains them.

---

## Tabs

| Tab | What is on it |
|---|---|
| Dashboard | Headline cost, p*, carbon; cost and carbon by unit operation; the cost-versus-assay curve; the caveats worth reading before quoting anything |
| Inputs | Every input, grouped, with unit, evidence status, confidence and source |
| Mass & energy | Recovery cascade, throughput, ion exchange, reagents, energy, water |
| Equipment & CAPEX | Itemised equipment with in-range flags, the capital build-up, three benchmarks, capital by unit |
| Operating cost | Variable and fixed lines, the per-kilogram cost stack |
| Cost by unit | Cost split across UP1–UP11, the physical allocation register, the reconciliation |
| Carbon | Electricity mix, route register, emissions by unit operation, mix versus 100% grid, the boundary statement |
| Finance | WACC, production cost, p*, the 31-year real cash flow |
| Policy | Four packages side by side, the financing build-up, the CMPTI eligibility register, the concession schedule |
| Sensitivity | Tornado and Monte Carlo on p*, production cost or carbon |
| Checks & sources | Internal consistency, workbook regression, documented divergences, evidence status, sources |

---

## What is verified, and what is not

At the shipped defaults the Python reproduces `OpenGa_v3.3_Carbon.xlsx` exactly:

| | Model | Workbook |
|---|---|---|
| Overall recovery | 0.25814010121445 | exact |
| Liquor throughput | 71.9432141075995 t/kg | exact |
| Electricity | 19.8262084394536 kWh/kg | exact |
| FCI | A$467,616,214.90 | exact |
| Cash cost | A$248.010575934/kg | exact |
| Production cost | A$697.398940145/kg | exact |
| p* | A$836.669203414/kg | exact |
| Carbon, all boundaries | 32.5958351096 kg CO₂e/kg | exact |
| Policy packages 2 and 3 | 815.769969 / 698.295970 | exact |

Checks at the defaults: **internal 14 of 14**, **regression 10 of 10**, seven
divergences reported as informational.

**This validates no input.** It confirms the arithmetic is internally consistent, that
allocations reconcile to their totals, that scopes are not double counted, and that the
port has not drifted from the workbook. It cannot tell you whether the feed assay, the
caustic dose, the completeness factor, any route price or any embodied emission factor
is right. Most of them are labelled PLACEHOLDER or ESTIMATE for exactly that reason —
the Inputs tab shows the status of every one.

Three things worth carrying into a presentation:

- **The feed assay is unmeasured.** No Australian refinery has published a gallium
  assay. The cost-versus-assay curve is the honest headline, not the single number.
- **The capital estimate leans on a completeness factor of 6.** The itemised equipment
  list is the weakest part of the model and the Equipment & CAPEX tab says so.
- **The carbon figure is a screening inventory, not a product LCA.** Its wider boundary
  is dominated by embodied chemical factors that are all unverified proxies, and the
  Bayer liquor carries zero upstream burden by a cut-off choice that an economic
  allocation would overturn.

---

## Layout

```
openga_v1/                backend, no Excel at runtime
  config.py               flat parameter set, categories, presets, structural switches
  _gen_defaults.py        generated from the workbook — regenerate, do not hand-edit
  meb.py                  mass and energy balance, both energy modes
  equipment.py            16 items, Towler & Sinnott correlations, in-range flags
  capex.py                the four capital methods
  opex.py                 variable and fixed operating cost
  allocation.py           the single allocation register cost and carbon both read
  energy.py               five-route electricity mix, blended price and factors
  carbon.py               scope 1 / 2 / upstream by unit operation
  finance.py              real DCF, production cost, closed-form p*
  policy.py               v3.1 module and the legacy WP4 scenarios
  analysis.py             assay curve, tornado, Monte Carlo
  validation.py           the check suite
  engine.py               orchestrator: run(ModelInputs) -> Results

app/
  streamlit_app.py        the interface
  charts.py               Altair builders

selftest.py               headline numbers and checks without a browser
```

The backend has no Streamlit dependency: `engine.run(ModelInputs())` works from any
Python script, which is how `selftest.py` runs.
