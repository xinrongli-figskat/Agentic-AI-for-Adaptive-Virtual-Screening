# D7-D Tier B: the inherited measurement definitions do not partition the data

Post-exposure. This is an incomplete measurement, not a shortlist judgment. The authorized D7 unit rule has been applied. No GLM was called and the gate table has not been applied.

## Trigger and concrete observations

D7 requires D6 A-1 measurement with three mutually exclusive fractions whose sum is one, while retaining D6 A-2's table unchanged. D6 defines `skeleton_only_frac` for `n_src = 1` when `skeleton_src` contains another source ID, and `single_source_frac` for `n_src = 1` when `skeleton_src` is empty. Tier B covers a rule not covering an observed case.

There are **2,526 saved support identities** with exactly one source, at least one alternative full key sharing their connectivity key, and **only the same source ID** among those alternatives. They satisfy neither definition. The final partial table has 62 rows; **8 rows** have a defined fraction sum of one and 54 do not. No residual was silently assigned to single-source. The saved denominator is the original R3 support count in every row.

The source-tier definition is also incomplete. It lists T1 `{7,21}`, T2 `{38}`, T3 `{1}`. In **43 of 62 assays**, the activity records supporting the saved identities come from **src_id 37**, which the locked ChEMBL 37 `source` table calls **BindingDB Patent Bioactivity Data**. It is distinct from src_id 38, **SureChEMBL Patent Bioactivity Data**. Source 37 has no specified branch. Treating it as 38 or as literature would change the rule.

There is a further source-scope ambiguity: source-tier assignment could use the provenance of these assay activity records, or all `compound_records` sources for the constituent molecules. These are not equivalent. The latter contains 34 source IDs absent from the listed mapping; both distributions and their provisional tier encodings are saved. This file does not select between them. Cross-source presence also does not itself prove independent experimental confirmation of a structure; these are provenance measurements.

## The authorized D7 multi-molregno change succeeds

All 62 support sets reproduce the locked R3 sizes and hit-support totals, totaling **25,813 standardized support identities**. There are exactly **five multi-molregno identity occurrences**:

| Assay | Multi identities / support identities | Fraction |
| --- | --- | --- |
| CHEMBL1738510 | 2 / 462 | 0.4329% |
| CHEMBL4257087 | 1 / 261 | 0.3831% |
| CHEMBL3431930 | 1 / 475 | 0.2105% |
| CHEMBL3431931 | 1 / 475 | 0.2105% |

All satisfy the <=1% de minimis clause and none is a stop reason. Two are classified as full-match by the explicitly authorized source union. The remaining three have an empty alternative-key source set for every constituent, so they are single-source under every possible representative or union choice. The first diagnostic snapshot conservatively left these three unassigned; the second snapshot records this invariant resolution and retains the first snapshot intact.

## Candidate resolutions and their costs

1. **Repair the partition and explicitly define provenance scope.** Change single-source to `n_src=1 and no alternative-key source outside the identity's source union`; use the assay-supporting activity provenance for source tier, keep global compound provenance only for credential counts, and explicitly add src_id 37 to a chosen patent branch. This produces the intended exhaustive three-way partition but requires a new authorized specification and may change eligibility. Any approval must state that it can make affected candidates easier to pass. T4 should then be defined by applying every involved component gate, rather than assuming that different metrics have an intrinsic strictness order.
2. **Add an explicit unresolved category and withhold affected candidate credentials.** Keep the original fractions and table unchanged, add a fourth measurement class, and defer sources outside the source map. This is conservative and preserves literal definitions but cannot meet the existing three-fractions-sum-to-one requirement or deliver 62 complete credentials.
3. **Restrict measurement to fully covered candidates.** Retain only candidates whose identities and source IDs are covered. This avoids remapping but changes the 62-candidate scope and cannot be substituted for the requested full table.

Recommendation: authorize option 1 in a new version after reviewing these measurement-only counts. Until then, retain the 62-row **partial** measurement, stop gate application and GLM reevaluation, and continue independent D7 work.

## Artifacts and interpretation

`credential_62_measurement_final_partial.csv` and `credential_summary_final_partial.json` are the final measurement-only summaries. The final table reports global and assay-provenance source readings separately and assigns no aggregate source tier; equality of these scopes is not a new requirement. Earlier diagnostic snapshots are retained. There is intentionally no success-shaped `credential_62.csv`, no `gate_decisions_62.csv`, and no new candidate decision. Real per-identity details and input hashes are in Git-ignored `identity_private/`. `gate_rule_lock.json` predates measurement and retains the original A-2 bytes. D3 registration is complete in `qualification_criteria_candidates.md`.
