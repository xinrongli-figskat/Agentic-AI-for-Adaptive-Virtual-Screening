# Source-gap adjudication rule (draft, post-exposure)

Date: 2026-10-18. This rule was drafted after the v2–v5 source reviews had been seen. It applies uniformly to candidates assessed after this date and creates no candidate-specific exception. It does not alter an existing frozen pool, label or qualification threshold.

## Classification

- `blocker`: The gap undermines the integrity of a label as a record. We cannot trust that the compound, measurement and class refer to one consistent experiment. This includes an erroneous or ambiguous label, or compound-dependent measurement conditions pooled as though they were one assay.
- `limited`: The recorded labels remain faithful and comparable inside the pool; the gap limits what may be inferred beyond that assay. Every controller is evaluated against the same labels, so the gap does not by itself compromise the internal controller comparison.
- `unverifiable`: Evidence is insufficient to decide between the preceding cases. Treat this as a blocker for campaign entry, while recording `unverifiable` separately: failure to verify is different from verified heterogeneity.

## Three questions, in order

1. Does the gap create a wrong or ambiguous label? If yes, `blocker`.
2. Could the gap make the experimental conditions differ among compounds? If yes, `blocker`.
3. Does it only constrain interpretation outside this pool? If yes, `limited`.

If the required evidence is unavailable, use `unverifiable`, with blocker effect. A missing quantity that is constant across the entire pool cannot by itself distort relative comparisons inside the pool and can fall under question 3. A missing quantity that may vary by compound belongs under question 2. Constancy must be supported by evidence; it is not assumed from a shared assay identifier alone.

## Requirements before a `limited` pool can enter a campaign

All three are required:

1. Its pool card names the gap and its scope, and preserves the provenance of each original record.
2. Conclusions are confined to assay-defined activity and explicitly make no claim of direct target binding.
3. Before freezing, a homogeneity assertion confirms that all records use one readout-column combination and accounts, by curation rule, for the difference between raw record count and usable compound count.

This is a post-exposure draft. It does not mark any candidate campaign-ready and does not rewrite prior v1–v5 decisions.
