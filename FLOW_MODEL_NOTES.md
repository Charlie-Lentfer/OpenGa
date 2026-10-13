# Flowsheet reporting basis

Calculation path: resolved V1 inputs → MEB → `streams.build_streams()` →
`Results.streams` → SVG → Streamlit image or iframe.

The original flowsheet adapter expected differently named dictionary fields.
V2 adapts it to the actual V1 MEB dataclass and keeps its stream IDs and routing.
No snapshot quantities, Downloads path, workbook or external image service are
used at runtime.

## Quantities and routing

All quantities are kg per kg of 4N gallium product. Ga/Al/V include elemental
equivalents present in hydroxides. Header metrics always show feed Ga,
product-to-feed Ga recovery and product Ga; the quantity selector changes the
input/output cards.

- Caustic solution cards include water at the model's NaOH concentration.
  V1's reagent costs use contained NaOH.
- HCl retains V1's 100% equivalent dose, not an assumed 36% delivered solution.
- Al is eluted and precipitated; V leaves through regeneration, following the
  supplied stream model. V1 exposes no alternative Al/V elution efficiencies.
- Wash Ga loss follows `WashRec` and leaves in S7. Ga not precipitated at UP7
  stays dissolved and leaves with centrate S22. These losses are not omitted
  when the recoveries change from 100%.
- Acid mist S12 is zero because V1 has no mist-loss calculation.
- V1 has no electrolyte recycle model. S30R is zero; S30P equals S30 and is
  shown at the neutralisation interface. A nonzero `EWRecycle` sent to the
  adapter is rejected rather than implying a modelled recycle benefit.
- The boundary includes raw water S10 once, excluding the internal water
  distributions. S30 is never added to its child streams at the boundary.
- Resin-cycle states represent retained metals, not the full resin-bed mass.
- Grouped outlets are presentation totals of separate streams, not new pipes.

## Reconciliation and limits

The register checks total mass and elemental Ga/Al/V across eleven units,
the electrolyte split and the reported boundary: 52 checks. It also identifies
negative or non-finite constituents. Closure does not validate an input.

As in the supplied adapter, downstream totals use a lumped liquid/water
balance. This is not a full speciation, charge or hydrogen/oxygen balance.
The S28 stream mass is not independently constrained to V1's electrolyte
concentration/density targets; those targets still drive V1's water calculation.
For example, at default inputs the reported S28 mass is about 32.708 kg,
whereas target electrolyte volume times density is about 31.277 kg.
This inherited difference is disclosed rather than forcing apparent agreement.
Reconciling these assumptions requires a separate MEB revision.

The stream totals do not replace V1's waste-cost or carbon estimates. No new
treatment cost or recycle performance is inferred by this UI extension.

## Preserved baseline

Recovery: 25.814010%; liquor throughput: 71.943214 t/kg Ga; electricity:
19.826208 kWh/kg; production cost: A$697.398940/kg; minimum viable price:
A$836.669203/kg. Original internal and workbook checks continue to pass.
The V1 calculation modules are unchanged except for attaching the stream
register in the engine, seeding the four Custom resin inputs from the existing baseline preset, and limiting baseline comparisons to the baseline.
