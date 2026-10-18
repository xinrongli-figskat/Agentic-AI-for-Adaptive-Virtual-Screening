# DYRK3 assay edge review (2026-10-14)

Scope: ChEMBL 37, target `CHEMBL4575`, assay `CHEMBL5363961`, IC50, provisional 1000 nM threshold. This note records interpretation of the user-run diagnostic at `/driveA/xinrong/agentic-screening/data/curation_review/edge_inspection_20261014T142008Z_8c7c90d8`. It is a curation note, not a frozen benchmark or campaign result.

## One unresolved compound

The parent audit has 232 distinct standardized compound identities, of which 231 have usable threshold support (116 hit; 115 nonhit). `CHEMBL1802358` (`activity_id=25624630`) is the sole unresolved compound. Its one selected-assay record reports `IC50 = 230 nM` with equality relation, but ChEMBL's `potential_duplicate` field is `1`. The declared discovery policy (`exclude_flagged_potential_duplicates_from_signals=true`) makes its `record_signal=unknown`, reason `source_potential_duplicate`; its compound state is `unknown`, reason `no_eligible_threshold_support`. This is **quality-policy exclusion of a reported potency**, not a statement that the compound is inactive or has no recorded experimental result.

ChEMBL describes `potential_duplicate` as a likely repeat citation of an earlier activity measurement rather than an independent measurement. This flag alone does not establish that the numeric potency is false. The record should remain in the curation audit, outside the provisional 231-compound campaign pool. Including it would require checking the source and any earlier corresponding measurement, writing a revised curation rule, and creating a new benchmark version before evaluation; it should not be changed to improve the active-search result.

## Fingerprint equality and analogue redundancy

Under the audit's Morgan radius-2, 2048-bit, chirality-enabled **bit** representation, 36 of the 231 usable compounds fall into 17 groups with identical bit fingerprints. Every displayed group contains different standardized structures. The first three groups demonstrate two patterns: (i) a three-member stereochemical series shares the same bit fingerprint **and** the same sparse count fingerprint; (ii) a cycloalkyl ring-size series shares the same bit fingerprint while its sparse count fingerprints and formulas differ. The first and second displayed groups are all hit support. All three mixed-support groups were subsequently inspected against the saved record-level values:

| Bit-fingerprint group prefix | Cyclohexyl compound | IC50 (nM) | Cycloheptyl compound | IC50 (nM) | Ratio, larger/smaller IC50 |
|---|---|---:|---|---:|---:|
| `049abe575052` | `CHEMBL5401658`, nonhit | 3277 | `CHEMBL5409493`, hit | 706 | 4.64 |
| `23483494b0fe` | `CHEMBL5394278`, nonhit | 1108 | `CHEMBL5423245`, hit | 758 | 1.46 |
| `af16aea44aef` | `CHEMBL5437222`, nonhit | 1877 | `CHEMBL5408457`, hit | 737 | 2.55 |

Within each pair, the displayed structures differ by one `CH2` in the cycloalkyl ring. All values have equality relation (`=`), units nM, and come from the selected DYRK3 assay. The **sparse count fingerprints differ in all three pairs**. The `1108`/`758` pair lies closest to the provisional 1000 nM cutoff: 1108 is only 10.8% above it. Each selected-assay molecule has one record in the audit, so this output provides no within-assay repeatability estimate. The ratios quantify reported IC50 differences, not statistical confidence.

Different structures with identical bit fingerprints are **not duplicate compounds**. The observed mixed-support groups are **not conflicting measurements for one compound**. They show a feature-resolution limit: any score depending only on these bit fingerprints must tie members of each equal-fingerprint group, so it cannot reliably prioritize the hit over the nonhit within a mixed group without other information or tie-breaking. This is a targeted modeling caveat, not a reason to alter the measured support labels. The previously reported Butina largest cluster (~31% of the usable pool) remains an analogue-concentration concern; scaffold/cluster/fingerprint counts do not prove independent chemical diversity.

## Provisional decision and work remaining

- Retain the 231-compound, 116/115 provisional pool for prototype-design review; retain the flagged compound separately as unknown. No decoys have been assigned.
- Keep the 1000 nM threshold as previously declared. The threshold-sensitivity counts (100, 300, 1000, 3000 nM) show strong class changes and must not be used to choose a cutoff after evaluating search performance.
- The full three mixed-support fingerprint groups and their original IC50 values have now been reviewed. Keep the primary bit-fingerprint baseline as originally proposed and preregister a count-fingerprint representation sensitivity check; do not use global hidden outcomes to tune a campaign agent. Investigate the potential-duplicate source only if considering its inclusion.
- Explicitly reassess the original 500-total priority gate: this 231-compound pool does not meet it. A narrower single-assay prototype qualification would be a documented compromise, not a pass under the old gate.
- Freeze a versioned benchmark and isolate its outcomes from campaign tools **only after** source review and criteria decision. The current audit and diagnostic contain labels and must remain in the curation workspace.

Primary source for the duplicate-field interpretation: [ChEMBL interface documentation, assay and activity questions](https://chembl.gitbook.io/chembl-interface-documentation/frequently-asked-questions/chembl-data-questions).
