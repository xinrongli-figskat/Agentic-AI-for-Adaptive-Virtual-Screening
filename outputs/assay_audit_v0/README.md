# Single-assay structure and measurement audit v0.1.1

This is a curation tool, not an LLM agent or a frozen screening benchmark. It reads the existing ChEMBL discovery run and the verified assay review package without network access. Default scope: DYRK3 / CHEMBL4575, assay CHEMBL5363961, IC50, provisional hit threshold 1000 nM.

## Run on the remote Ubuntu machine

```bash
cd /driveA/xinrong/agentic-screening
source .venv/bin/activate
python assay_audit_v0/tests/test_audit.py
python assay_audit_v0/audit_assay.py \
  --discovery-run /driveA/xinrong/agentic-screening/data/candidate_discovery/discovery_20261014T122202Z_5a03ac52 \
  --source-review /driveA/xinrong/agentic-screening/data/exploration/assay_review_transfer_20261014/source_review_combined.json \
  --output-dir /driveA/xinrong/agentic-screening/data/curation_review
```

Dependencies are the already-installed RDKit and Python standard library. The tool uses CPU and no GPU, API key, internet request, or GLM calls. Each execution creates a new output directory. Raw source files remain untouched.

The unit tests use explicitly synthetic records, not scientific benchmark data. Local verification used Windows Python 3.12.14, RDKit 2026.09.1 and NumPy 2.2.6; remote Python 3.10.12 should run the included tests before processing actual data.

## What the four stages do

1. Verify the saved source-code hash, the selected target's complete IC50 acquisition, page offsets, raw response hashes and unique activity IDs. Select this assay and reproduce its saved initial support counts. Partial target windows are rejected, so do not apply this directly to the incomplete BACE1 or Prothrombin windows.
2. Parse structures. Retain a single carbon-containing fragment and apply RDKit Cleanup. Quarantine ambiguous mixtures, invalid structures, radicals and unsupported elements. Use canonical isomeric SMILES as primary identity, preserving isotopes and specified stereochemistry. Uncharging is reported only as an alternative grouping; tautomers are not silently merged. Report source-ID collisions, unspecified stereocenters and parent changes.
3. Reconcile eligible IC50 evidence within the assay. Convert supported concentration units, preserve censoring relations, quarantine threshold disagreements and incompatible bounds, flag hit evidence with inactive/inconclusive source annotations. Keep unknown and excluded records and their reasons. Report exact-measurement spread without averaging. Produce threshold sensitivity counts at 100, 300, 1000 and 3000 nM; these are diagnostic comparisons and do not select an endpoint for best agent performance.
4. For the provisional usable pool, compute exact/generic Murcko scaffold groups, Morgan fingerprints (radius 2, 2048 bits, chirality), nearest-neighbor similarity and Butina clusters. Assess budgets 50/10 and 100/20 (total/initialization), with initialization included and feedback batches of 10. Calculate random expected hits and hypergeometric probabilities of single-class initialization. These are numerical feasibility checks, not campaign results.

Source provenance stays linked via source responses, URLs, hashes, activity IDs, assay/document IDs, original measurements and original structures. The selected raw activities are copied into the result directory for inspection.

## Main outputs

| File | Meaning |
|---|---|
| summary.json | Compact counts, initial-vs-standardized evidence, sensitivity, diversity and budgets |
| raw_selected_activities.json | Original records for the selected assay |
| records_audit.csv / .json | Original and normalized measurements/structures, exclusions and source IDs |
| molecule_id_audit.json | Source molecule IDs with structural ambiguity or failure |
| compound_audit.csv / .json | Standardized identities, all linked source IDs, provisional class and review flags |
| budget_feasibility.json | Pool fractions, random expectations and initialization risks |
| review_notes.md | Consequential choices and required manual decisions |
| run_metadata.json | Software versions, completion/error, costs and scope |
| source_receipts.json | Source page paths, URLs and verified hashes |
| OUTPUT_SHA256_MANIFEST.json | Integrity hashes for output files |

Source-ID counts and standardized-compound counts are different units. Quarantined structure IDs do not appear as negative compounds. A standardized compound with only unknown evidence retains the unknown state. Both assay-defined hit and nonhit evidence concern this endpoint under these experimental conditions; neither proves direct binding or universal biological inactivity.

## Interpretation limits and review decisions

The original candidate priority thresholds (500 total, 30 hit support, 100 nonhit support) remain a historical draft, not a brief requirement or automatic qualification. This tool creates no new qualification pass. Inspect structural exclusions, merged identities, censored disagreements, exact-value spread and analogue concentration before deciding whether the dataset supports the prototype.

Multiple carbon-containing components, including some organic counterions, are conservatively quarantined rather than automatically retaining the largest fragment. This choice can exclude valid salt records and must be reviewed. Cleanup can affect representation; charged identity, uncharged sensitivity and original structures are retained for inspection.

Scaffold/cluster counts depend on representation and are not proof of broad chemical coverage. A Butina cluster is a greedy centroid group, not an all-pairs equivalence class. A 0.85 similarity threshold marks close neighbors for review, not chemical identity. Exact pairwise analysis is limited to 1000 provisional usable compounds.

Final criteria, pool/labels, initialization, feedback schedule and budget must be reviewed and versioned before campaign evaluation. Every campaign version must be fixed; future campaign agents must not access these outcome-containing curation files or public bioactivity lookup tools. Controlled query isolation and both GLM controllers are subsequent work.

## Primary software references

- [RDKit standardization](https://www.rdkit.org/docs/source/rdkit.Chem.MolStandardize.rdMolStandardize.html)
- [Murcko scaffolds](https://www.rdkit.org/docs/source/rdkit.Chem.Scaffolds.MurckoScaffold.html)
- [Morgan fingerprint generation](https://www.rdkit.org/docs/source/rdkit.Chem.rdFingerprintGenerator.html)
- [Butina clustering](https://www.rdkit.org/docs/source/rdkit.ML.Cluster.Butina.html)
