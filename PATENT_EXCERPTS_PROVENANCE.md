# Provenance of the two patent value excerpts

Two files in this repository record activity values transcribed from granted patents:

- `outputs/acc2_patent_us8835472_sample_values.json` — 12 values from **US8835472B2**
- `outputs/tace_patent_us9926281_sample_values.json` — 12 values from **US9926281B2**

They are published deliberately. This file explains why, so that a future scan does not
flag them again.

## Why they are not a disclosure of evaluation-set results

1. **They contain no molecular identity.** Neither file carries a SMILES string, an InChI
   or InChIKey, a compound key, a ChEMBL molecule identifier or a `molregno`. The first
   records patent example numbers against IC50 values; the second records ChEMBL activity
   identifiers against patent compound numbers and values. Without identity there is no
   compound-result pairing, and so no label.
2. **Neither candidate is an evaluation set.** `CHEMBL3705476` and `CHEMBL5733557` were
   both held at source review and never admitted. The evaluation sets are `CHEMBL1738510`
   and the DYRK3 negative control.
3. **The values are already public at their source.** Both are granted US patents and the
   values are the applicants' own published data. Twelve values with line references is
   ordinary citation of a primary source.

## Why they are kept

They are the evidence for two admission decisions. The first records a mass-spectrometry
inconsistency — a reported [M+H]+ of 361 against a structure implying about 362.2 — that
held one candidate. The second records multi-example name collisions that could not be
reconciled against the deposited structures, which is the failure that motivated the
structure-identity admission criterion. Removing these files would remove the basis for a
reported finding.

## Scope rule

The prohibition that governs publication is on **per-compound results belonging to an
evaluation set**, and on any artifact pairing an evaluation-set member's identity
(compound key, structure, InChIKey, `molregno`) with a result or activity value. Source-review
evidence for candidates that were never admitted, consisting of values already public at
their source and carrying no molecular identity, is permitted — including in a public
repository.

These two files are byte-identical to their originals and are referenced by hash elsewhere in
the project record. They must not be edited.
