# D3-1 homogeneity and measurement-depth rule v3

Date: 2026-10-19. Definition-level, post-exposure revision. Lock SHA-256 and UTC before H3 redo or H7 results. Preserve the first-run and v2 assertions, blockers, and the successful 485-to-462 reconciliation byte-for-byte. H1/H2 were passed in v2 and are not rerun. Applies to subsequently reviewed deposited dose-response assays, not a TNAP-only exception.

## H3 mechanical correction

Classify all present auxiliary tid names by their *family*, accepting any ordinal point number for `% inhibition at ...uM_<ordinal>_point_RangeN` and `Excluded_Points_<ordinal>_point_RangeN`. Existing per-range IC50 numeric fit, qualifier, standard error, and Hill slope families remain unchanged. This changes only matcher coverage, not the H3 scientific predicate: every present auxiliary tid must be explained as the same assay protocol on the same target; an independent endpoint, other target, counter-screen, cytotoxicity, or separate protocol fails. Report family tid counts and coverage ranges, not individual IDs. Any unmatched tid after this correction is a hard stop.

## H7: measurement depth is now a gate

H7a: Determine what the existing 1–21 proxy counts from deposited AID 1056 column names, row structure, and protocol: concentration points, independent fits/runs, range blocks, or unknown. Distinguish an inferred proxy from verified independent experimental repeats. Unknown meaning is `unverifiable` with blocker effect.

H7b: For *usable standardized compounds*, partition by depth=1, 2–5, 6–10, >10; report compound count, hit count, and hit fraction per stratum, plus separate hit and measured-nonhit depth distributions. Define depth for a compound with multiple source rows as the minimum underlying per-row fit count, a conservative support measure; also report the maximum and count of compound-level row multiplicity. Explicitly state whether any stratum has substantial representation of both classes; do not infer causal selection from correlation alone.

H7c: For depth=1 compounds, report exact (`=`) versus censored `IC50_Mean_Qualifier`, IC50 range and order-of-magnitude span. Examine their complete available *within-fit* dose-point series and fitting metadata, rather than equating one fit with one concentration. If a depth=1 `=` IC50 is supported by a full concentration-response series from one fit, classify `limited`; if it is unsupported by available underlying data, classify `blocker`; if the depth proxy meaning is indeterminate, classify `unverifiable`. A censored bound is not an exact fit. Record any examples that lack enough source data without silently excluding them.

H7d: For the 13 usable compounds with exact [800,1250] nM results previously identified in H6, report their depth distribution and the number at depth=1. If most are depth=1, flag this in any later pool card.

## Locked decision table

- Depth proxy meaning cannot be determined: `unverifiable`; hard stop, no pool.
- Depth=1 exact IC50 values cannot be supported by their underlying data: `blocker`; hard stop, no pool.
- Depth=1 exact IC50 values can be supported by complete single-fit concentration series: `limited`, subject to all other frozen qualification gates. Any later pool card and D3 conclusion must state variable depth (1–21, median 1 if confirmed), its label association (v2 AUC 0.8785348526 and r 0.4948945406), and that the pool compares deeply characterized actives with thinly measured nonhits rather than uniform measurement effort. This remains an interpretive limitation and possible selection effect, not label leakage or causal proof.

The H5 association was a non-gate in v2; its magnitude warrants this stricter H7 gate. This is a prospective tightening after exposure, not blind validation. No threshold or original qualification criterion is changed.
