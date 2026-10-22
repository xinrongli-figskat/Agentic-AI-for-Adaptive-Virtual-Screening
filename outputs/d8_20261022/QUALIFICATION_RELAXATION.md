# Qualification criteria: strict catalog and teaching-prototype admission

The strict screen is retained as a catalog of public-data quality problems. The project is a pedagogical prototype, not a production benchmark. In the context of scarce suitable assay data, a documented source or endpoint limitation may be accepted for an explicitly source-limited prototype set. Such admission does not convert uncertainty into evidence and does not imply that a measured inhibition value proves direct binding.

## Criteria retained as strict safeguards

- A sufficient number of experimentally measured nonhits, with adequate chemical diversity.
- A low probability that initialization contains only one measured class.
- A bounded largest chemical cluster and a minimum number of scaffold groups.
- A selection budget that queries only a limited fraction of the pool.
- No use of unmeasured presumed negatives as experimentally measured nonhits.

These concern whether the evaluation can support an interpretable comparison; they are not merely obstacles caused by sparse public data.

## Criteria relaxed for a teaching prototype

- Endpoint documentation need not resolve every mechanistic detail if the assay’s reported measurement is explicit enough to define the measured outcome. The result must be named as assay-defined activity or inhibition, with uncertainty stated; it must not be described as direct binding without direct evidence.
- Unresolved source questions need not all be cleared before a limited prototype run if compound identities are sufficiently usable and the unresolved questions are clearly carried into the set’s limitations. A source concern that prevents determining which molecule was measured remains a blocker.
- An association between source measurement effort and measured class is recorded and reported, but is not by itself an admission veto. Measurement effort is excluded from model inputs and its impact is disclosed.

## Quality issues remain catalogued

The D3–D7 work identified three recurring issues: measurement effort can be strongly associated with measured class; patent compound identities may be difficult to verify; and some prediction-method settings leave little performance difference for a controller to exploit. The funnel of 62 numerically passing assays, six focused source reviews, and one source-limited evaluation set remains part of the evidence. Relaxing admission does not erase these findings or repair historical classifications.

## Re-evaluation boundary

The 62-candidate table must be recomputed from saved public and source-review fields, without reading hidden campaign outcomes to choose candidates. This file records the policy; it does not freeze a new set, create new labels, or authorize a new active-search run. A candidate accepted under the relaxed rule must be labelled source-limited and tied to a separate version before any future evaluation.

## Post-exposure re-evaluation of the saved 62

The saved R3 table and D7-D identity audit were joined by assay identifier. All 62 remain numerical passes. In the strict saved identity table, 0/62 were marked campaign-ready. Applying the teaching-prototype interpretation while retaining the identity check yields **one currently usable, source-limited set** (the existing TNAP set), **two additional source-tier-1 rows eligible for limited source review but not yet admitted**, and **59 rows not admitted because the saved identity evidence is unresolved**. This is not a claim that endpoint/source limitations have been resolved for the two additional rows, and it does not override the existing D7-D status. No new set was frozen and no active-search run was started.

For a transparent queueing aid, the 62 were ranked by measured nonhit support multiplied by the number of scaffold buckets (including the acyclic bucket), descending, with assay identifier as the tie-break. This is a post-exposure descriptive ordering, not an admission score:

| Rank | Assay | Measured nonhits | Scaffold buckets | Product | Current relaxed status |
|---:|---|---:|---:|---:|---|
| 1 | CHEMBL5731108 | 854 | 159 | 135,786 | Identity evidence unresolved |
| 2 | CHEMBL3431931 | 443 | 210 | 93,030 | Limited source review candidate; not admitted |
| 3 | CHEMBL2328568 | 328 | 278 | 91,184 | Identity evidence unresolved |
| 4 | CHEMBL3431930 | 428 | 210 | 89,880 | Limited source review candidate; not admitted |
| 5 | CHEMBL5736425 | 410 | 203 | 83,230 | Identity evidence unresolved |

The full row-level result is `relaxed_admission_62.csv`; machine-readable counts are in `RELAXED_ADMISSION_62_SUMMARY.json`. The ranking deliberately cannot turn a large pool into an admitted set: source-level molecule identity remains a separate requirement.
