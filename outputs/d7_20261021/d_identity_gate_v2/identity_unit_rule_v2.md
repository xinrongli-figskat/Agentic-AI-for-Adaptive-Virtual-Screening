# D7-D structural identity measurement unit v2

Post-exposure. This is a measurement specification; it does not approve a shortlist or create a campaign-ready pool.

Authority: D7 task card, D-1, dated 2026-10-21. D6's blocker remains unchanged.

1. The measurement unit is each saved standardized support identity used in R3 (usable hit support or measured nonhit support). Do not expand or restandardize this set.
2. For each identity, n_src is the cardinality of the union of compound_records.src_id across every constituent molregno.
3. Keep multi_molregno_count per assay; the total across 62 assays must equal five.
4. A multi-molregno fraction <= 0.01 is de minimis and does not stop measurement. A fraction > 0.01 is a candidate-specific Tier B stop.
5. D6-A A-2's G1/G2 thresholds and text are preserved byte-for-byte in a separate gate-rule extract. They are not applied in the first wave.
6. D6-A A-1's other definitions remain in effect. Unspecified measurement or source-tier cases must be recorded as Tier B; do not silently choose or extend a definition.

Lock this file and the exact D6-A A-2 extract with SHA-256 and UTC before producing measurements. All per-identity source details remain in identity_private/. No GLM calls are authorized in this first-wave measurement.
