# D6-A Tier B blocker: standardized support identity maps to multiple molregnos

This file preserves a D6-A specification mismatch. D6 is post-exposure and this record does not create a benchmark, a shortlist, or a campaign result.

## Triggering D6 clause

The Tier B protocol requires a stop when the locked rule and the actual data structure do not specify how to proceed. A-1 defines every member of the R3 support set as taking one `compound_structures.standard_inchi_key` and defines `n_src` as the number of distinct `src_id` values for **that `molregno`**. Its requested output, however, has one row-level credential per saved standardized support compound.

## Observation

The 62 saved R3 curations contain 25,813 usable support identities. 25,808 carry one `molecule_chembl_id`; five carry two. The five records are in assays `CHEMBL3431930`, `CHEMBL3431931`, `CHEMBL1738510` (two records), and `CHEMBL4257087`.

The duplicated identifiers are not interchangeable aliases. They include parent versus salt representations after the existing curation normalization; e.g. a TNAP support identity contains a parent and a dihydrochloride ChEMBL record with distinct full InChIKeys. Thus there is no single `molregno` for these standardized support identities. The locked A-1 text supplies no aggregation, representative-selection, or expansion rule.

No credential table, gate decision, or GLM call was produced.

## Candidate resolutions

1. Use a deterministic representative `molregno` for each merged identity, such as the numerically lowest one. This preserves the R3 support-set count but arbitrarily discards source provenance attached to the other normalized member.
2. Treat the saved standardized support identity as the measurement unit and union the `src_id` values across all of its source `molregno` values. This preserves R3's 62 candidate counts and all recorded provenance, but changes the A-1 phrase that defines `n_src` for a singular `molregno`.
3. Expand each merged standardized identity to one row per `molregno`. This follows the singular wording, but changes R3's support-set cardinalities and makes the requested 62-row candidate summaries incomparable with the locked `N` and `K` values.

## Recommendation

Adopt option 2 only through a new, explicitly versioned rule: compute a credential for each **saved standardized support identity**, aggregate its provenance over every original `molregno` listed in `molecule_chembl_ids`, and retain a count of multi-molregno identities. It matches the existing curation's unit of analysis without hiding salt/parent provenance. This is a specification choice, so this task does not implement it without direction.
