# OpenGa app V2

Gallium Recovery Cost and Emissions Assessment: the OpenGa model with a live
flowsheet, in a step-by-step UNSW-styled interface that matches the copper
value-chain tool. Use this folder as your app project.

Developers: Charlie Lentfer (lead developer) and Rahman Daiyan (supervisor), UNSW Sydney.

## Run locally

Open a terminal in this folder:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run app/streamlit_app.py
```

Python 3.11+ is required by the dependencies. V2 was tested with Python 3.13 (model) and 3.11 (this interface)
and the exact versions in `requirements.txt`. On Windows, activate the virtual
environment with `.venv/Scripts/activate` instead.

Start on **Overview**, then work through the five *Build the scenario* steps in
the sidebar. Nothing is calculated until you press **Run model** (sidebar or the
foot of any step). If you edit an input after a run, results fade behind a banner
until you run again. Select the **Custom** resin preset on step 2 before editing
ion-exchange performance; named presets intentionally override those inputs.

## Deploy

See [DEPLOY.md](DEPLOY.md) for creating the GitHub repository and the Streamlit
Community Cloud app. Main file path: **`app/streamlit_app.py`**.

The backend is still named `openga_v1` for import compatibility; this is expected
inside V2. The MEB, equipment, energy, cost, finance and carbon equations are
unchanged. The flowsheet is a reporting extension, not a replacement MEB.

## New code and fixes

| File | Purpose |
|---|---|
| `openga_v1/streams.py` | Builds 37 live stream records from V1's MEB |
| `openga_v1/stream_metadata.json` | Descriptions and routing; no snapshot quantities |
| `openga_v1/engine.py` | Exposes the register as `Results.streams` |
| `openga_flowsheet/flowsheet.py` | Earlier card-style flowsheet renderer; kept for `tests/test_streams.py`, no longer shown in the app |
| `openga_flowsheet/app_flowsheet_tab.py` | Display wrapper for that renderer; no longer used by the app |
| `app/streamlit_app.py` | Entry point: page navigation, sidebar run status, Run and Reset |
| `app/views/` | One file per page (overview, five steps, three results pages) |
| `app/state.py` | Inputs, method choices, the Run snapshot and the stale check |
| `app/ui.py` | UNSW header and footer, callouts, How-to panels, cards and chart frames |
| `app/charts.py` | Altair charts |
| `app/lcop.py` | Splits the LCOP into operating cost, capital recovery, company tax and support |
| `app/pfd.py` | Process flow diagram (SVG) on the project's block-flow layout, stream numbers as in the register, live values in hover tooltips |
| `app/assets/` | UNSW logo and favicon |

Custom resin inputs are now populated from V1’s existing baseline preset, so Custom mode can run and accept edits. Input edits now apply before the model runs. Repeated IX recovery controls
have distinct keys, stay synchronised, and reset correctly. Workbook regression
is compared only at its applicable baseline; modified scenarios are no longer
incorrectly marked as baseline regression failures.

The Process page draws the flow diagram from the live stream register:

```python
from openga_v1 import engine
import pfd                        # app/pfd.py

results = engine.run(model_inputs)
svg = pfd.svg(results.streams, results.meb)
```

## Checks

```sh
python selftest.py
python -m unittest discover -s tests -v
```

The self-test includes the original 14 internal and 10 workbook checks plus
52 stream balance checks. Integration tests cover scenario changes, stream
conservation, live image updates, every page before and after Run, the stale
banner, reset, resin locking, capital and policy methods, and the Monte Carlo.

Read [FLOW_MODEL_NOTES.md](FLOW_MODEL_NOTES.md) for the reporting assumptions
and [MODEL_NOTES_V1.md](MODEL_NOTES_V1.md) for the original model documentation.

## Interface

The app reports one cost: the **levelised cost of production (LCOP)**, the constant
real price per kg of 4N gallium at which the plant earns its cost of capital after
company tax. In the model this is `finance.pstar`; no model equation changed.

| Page | What it shows |
|---|---|
| Overview | What the model does, the process in five cards, the questions it answers, scope, workflow and developers |
| 1. Feed liquor and plant basis | Capacity and liquor chemistry; after Run, liquor flow and feed gallium |
| 2. Gallium recovery process | Resin preset, energy model, recovery cascade, reagents, electrowinning; after Run, the process flow diagram, stream table and balance tables |
| 3. Capital and operating cost | Capital cost method, equipment, capital factors and prices; after Run, the LCOP bridge for every support package (selected one solid, others dashed) and cost detail |
| 4. Energy and carbon | Electricity mix and emission factors; after Run, carbon intensity and the route register |
| 5. Finance and policy support | Policy model, package for results, tax, WACC, CMPTI and grant terms; after Run, what each package is worth |
| Results summary | LCOP and scope 1 + 2 carbon as headline numbers, LCOP by package and plant figures on one line each, three charts with reading notes, caveats, glossary and CSV download |
| Uncertainty | Tornado on LCOP or carbon, and the Monte Carlo |
| Methods, checks and sources | How the LCOP and carbon are calculated, allocation rules, model checks, evidence status and sources |

Every step page has a *What this page does* box and a *How to use this page* panel.
Inputs sit in numbered expanders, two per row, each with an evidence badge (Cited,
Assumption or Placeholder) and its source in the help tooltip.

Results are always calculated from the inputs captured when **Run model** was
pressed (`state.run`), never from inputs typed since, so every panel matches the
run it says it is from.

The earlier terms map onto the LCOP build-up as follows: *cash operating cost* is the
operating cost; *capital charge* is capital recovery; *production cost* (their sum) was a
pre-tax figure and is no longer shown; *p\** is the LCOP.

The UNSW logo is used as in the copper value-chain tool. Confirm with UNSW
that the logo may be used on a public deployment before publishing.

The `openga_v1` backend name is retained for compatibility. The MEB, energy,
equipment and financial equations are unchanged.
