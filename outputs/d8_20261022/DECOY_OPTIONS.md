# Decoy options and measurement plan

Decoys are compounds treated as presumed inactive for a defined computational comparison. They are not experimentally measured nonhits. Experimentally measured nonhits also require checks for chemical diversity and systematic differences from actives.

| Type | Construction | Main bias or limitation | Availability here |
|---|---|---|---|
| Property-matched presumed inactives (DUD-E style) | Select compounds matching simple physicochemical ranges while avoiding similarity to known actives | Matching can create obvious topological or property differences; presumed inactivity can be wrong | Can be generated from a public compound library after documenting filters; not currently generated |
| Latent-active filtered decoys (DEKOIS style) | Filter candidate decoys against known or predicted activity and similarity rules | Depends on activity coverage and filtering model; may remove plausible hard negatives and create selection bias | Possible if a sufficiently broad assay and structure set is assembled; not currently run |
| Random screening-library compounds | Sample from the same preset library without activity measurements | May make classification artificially easy if chemistry or source differs; some may actually be active | Constructible from the local public compound pool, but labels remain presumed |
| Measured actives at a related target | Use experimentally active compounds for a related target as selectivity decoys for the target under study | Selectivity is not guaranteed; target-family and assay differences matter | Most attractive local option if compatible measured assays and source records are found; report as measured related-target activity, not target nonhit |
| Time-split or prospective decoys | Use compounds measured later, or compounds prospectively tested and found inactive | Requires a trustworthy date split or new prospective measurement; temporal chemistry shifts can dominate | Not presently available without new data or experiments |

## Recommended option

If a decoy sensitivity analysis becomes necessary, first examine experimentally measured actives at a related target. This is constructible from assay data and avoids fabricating an inactive label. It must be called a selectivity comparison, not a target-specific nonhit set, and the related assays need their own source and endpoint review. It should remain separate from any target-specific measured pool.

## Evaluation required for every set

Report performance of (1) a structure-only method that receives no measured labels and (2) a label-permutation control. These estimate how much apparent separation can arise from structural artifacts or chance label association. Apply the same two controls to experimental active/nonhit sets: measured nonhits can also differ systematically from actives for trivial reasons.

The project has already run both types of control. On TNAP, the bit-fingerprint structure-only ranking retrieved a mean 11.85 actives in 50 selections, versus 6.00 for uniform random selection; the label-permutation arm retrieved 3.85. The measured-label fixed rule retrieved 20.35. On DYRK3, the structure-only ranking was only 2.75 actives above random selection on average (95% paired interval 1.45 to 4.15); the measured-label fixed rule exceeded the label-permutation arm by 2.15 (95% interval −0.95 to 4.90), which includes zero. TNAP values are in `outputs/d3_tnap_20261019/d3_6_report/aggregate.json`; DYRK3 contrasts are in `outputs/d_discrimination_20261018/d1_descriptor_association_private_/paired_decomposition.csv`. These controls are method checks, not proof that every source difference has been removed.
