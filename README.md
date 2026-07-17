# OpenGa

**Open techno-economic & carbon model for gallium recovery from spent Bayer liquor** (Route 1: filter press → ion exchange → wash → acid elution → precipitation → centrifuge → purification → electrowinning → refining to 4N).

OpenGa is a faithful, regression-tested Python port of two source-of-truth workbooks:

| Workbook | Scope | OpenGa modules |
|---|---|---|
| `WP3_Balance_v3_3.xlsx` | mass & energy balance | `config`, `meb`, `carbon` |
| `Ga_Financial_Model_WP4_v2.xlsx` | financial model | `config`, `upcost`, `finance`, `policy`, `validation`, `sensitivity`, `montecarlo` |

The workbooks remain authoritative. Every backend module **reproduces their cached values via `pytest`** (`tests/baseline.json` is generated directly from the workbook caches by `tools/build_baseline.py`). This test gate is a milestone that must pass before any frontend work.

> ⚠️ **Placeholders.** All carbon emission factors and many unit prices are PLACEHOLDERS (flagged in `config.py` and surfaced in results). Do not quote results before sourcing them.

## Layout

```
openga/            # model layer — zero UI imports
  config.py        # all WP3/WP4 defaults as dataclasses, each with its REF citation
  meb.py           # 11-UP mass & energy cascade -> per-kg export vector
  carbon.py        # scope-tagged emissions (S1/S2/embodied) + Luo GWP validation
  upcost.py        # variable OPEX per unit operation (+ reconciliation invariant)
  finance.py       # CAPEX, OPEX, LCOP and closed-form minimum viable price (MVP p*)
  policy.py        # baseline / CMPTI+EFA / CMSR scenarios; CMPTI eligibility; neutrality check
  validation.py    # Luo carbon check + Wesselkaemper year-indexed replication engine
  sensitivity.py   # tornado + break-even feed-concentration sweep
  montecarlo.py    # correlated triangular draws -> MVP distribution
  cli.py           # `python -m openga.cli <module>`
app/               # interim Streamlit UI (disposable; to be replaced by OpenCu layout)
tests/             # one file per module, checked against baseline.json
tools/             # build_baseline.py — regenerate the fixture from the workbooks
```

The model layer imports no UI. The frontend (`app/`) is replaceable: section K will swap in Rasmeet's OpenCu-derived Streamlit layout and re-point widgets at the same `openga/` functions with **no backend change**.

## Install

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install -e .            # optional: exposes the `openga` CLI entry point
```

Backend-only use needs just `numpy`.

## Run — per-module CLI

```bash
python -m openga.cli meb           # mass & energy balance (per kg 4N Ga)
python -m openga.cli carbon        # emissions, two boundaries (PLACEHOLDER EFs)
python -m openga.cli upcost        # variable OPEX per unit operation
python -m openga.cli finance --policy 1   # FCI, OPEX, LCOP, MVP p*
python -m openga.cli policy        # all three scenarios side by side
python -m openga.cli validation    # Wesselkaemper replication tests
python -m openga.cli breakeven     # MVP vs feed Ga concentration
python -m openga.cli montecarlo --trials 2000 --seed 42
python -m openga.cli all
```

Programmatic:

```python
from openga import meb, finance, policy
res = meb.run()                       # MebResult; res.export is the per-kg vector
fr  = finance.run(policy=policy.scenario(1))
print(fr.mvp)                         # 933.38 AUD/kg (baseline)
```

## Interim UI

```bash
streamlit run app/streamlit_app.py
```

Pages mirror the workbook structure: Process & MEB · Cost per UP · Carbon · Financials & MVP · Price Ladder · Break-even · Sensitivity/Monte Carlo · Policy Scenarios · Validation.

## Tests (milestone gate)

```bash
pytest -q
```

Regenerate the baseline after any workbook change:

```bash
python tools/build_baseline.py --wp3 WP3_Balance_v3_3.xlsx --wp4 Ga_Financial_Model_WP4_v2.xlsx
```

## Headline reproduced values (baseline, Australian scenario)

| Quantity | OpenGa | Workbook |
|---|---|---|
| Liquor throughput | 48.8515 t/kg | 48.8515 |
| Electricity | 143.558 kWh/kg | 143.558 |
| Overall Ga recovery | 25.836 % | 25.836 % |
| Carbon S1+S2 (placeholder EFs) | 77.73 kg CO₂e/kg | 77.73 |
| Carbon +embodied | 215.41 kg CO₂e/kg | 215.41 |
| **Minimum viable price p\*** | **933.38 AUD/kg** | **933.38** |
| Wesselkaemper base LCOP | 434.18 US$/kg (target 421.98, ✓ ±5%) | 434.18 |

## Validation

- **Physics/inventory** — validated against **Luo et al. (2025)** (set scenario 1 + resin preset 4; `carbon.validate_luo`).
- **Financial engine** — validated against **Wesselkaemper et al. (2025)** base case, capital component, two out-of-sample demand-cap scenarios, and the US$120M grant case (`validation.wesselkaemper`), all within their designed tolerances.

## Open items

- **Revenue-side price floor (CMSR)** is intentionally **not wired** into `p*` — the contract mechanics are undecided; carried as an OPEN TODO (`policy.PRICE_FLOOR_TODO`).
- **Section K** — swap the interim UI for Rasmeet's OpenCu layout + results download (xlsx/csv), same backend.
- **Section L release** — tag a GitHub release and archive on Zenodo for a DOI (Thesis C citation target).

## Licence

MIT — see `LICENSE`. Please cite via `CITATION.cff`.
