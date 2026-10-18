# Task 1 follow-up: prospective search rules and execution plan

Date: 2026-10-16 (Asia/Shanghai). This is a post-exposure exploratory extension. The earlier Task 1 runs, DYRK3 data, and campaign results have already been seen. Nothing here turns an earlier rejection into an acceptance or makes a blind-validation claim.

## What the completed search established

The closed v3 run ended with no review shortlist. It examined only three target profiles in the new v3 stage, and it did not produce new assay-specific count probes. The wider saved history has 64 IC50/type-B target count probes, but target counts are activity records, not distinct compounds. Several larger targets have not received a target profile. Existing previews show that large target totals can still consist of many small assays.

The existing fixed source holds remain assay-specific: CHEMBL5737918 (p300) and CHEMBL5732233 (P2X2 catalog assignment). They do not exclude other assays for those targets.

## Candidate qualification rules for the next prospective review

Keep the already reviewed two-tier size rule for this next search: 250–499 curated usable compounds is a limited-feasibility candidate; 500 or more is preferred. Require at least 30 hit-support and 100 nonhit-support compounds under the existing IC50 <=1000 nM endpoint, confidence score >=9, assay type B, single-protein mapping, complete assay retrieval, and the existing structure, conflict, diversity, and initialization checks.

These thresholds remain operational choices, not requirements in the brief or universal scientific standards. The 50-query campaign implies a pool of at least 250 under the current <=20% query-fraction rule. Do not change the thresholds after seeing new curated labels. If this search yields no candidate, report that result and broaden the source or endpoint in a separately reviewed protocol version.

## Data-first screening policy

1. Reuse hash-verified historical evidence first. Never repeat a successful identical ChEMBL request when the raw response is already present and hash-valid.
2. Rank only current-release single-protein targets with IC50/type-B counts. Treat a target count as a record-volume signal only.
3. Profile unprofiled targets with at least 250 records in descending count order, initially up to four targets per batch. The currently exposed queue begins with CHEMBL4158 (1864), CHEMBL3797 (1630), CHEMBL4333 (1474), CHEMBL4691 (840), and then CHEMBL3501 (495) / CHEMBL5476 (486) as smaller exploratory options. Their class balance and assay compatibility are unknown until inspected.
4. For already profiled high-volume targets, list assays and count promising assay IDs before full acquisition. A raw assay activity count below 250 can justify stopping that assay under this protocol; a partial-window class preview cannot.
5. The program presents the four highest-count, not-yet-profiled target options, using counts already stored in the closed run. The LLM selects one target at a time, then chooses assay-level follow-up actions from the returned evidence. The numerical tools establish record counts and curation metrics; the LLM does not invent counts or override fixed qualification gates.
6. Full retrieval and chemical curation follow only after a candidate assay passes an exact count screen and metadata review. Keep activity records with inequalities; preserve unknown and conflicting outcomes separately; never treat unknown as inactive.

## Current visible assay leads

The v3 closed state includes incomplete target-window previews. The larger class-support previews are CHEMBL5737918 at p300 (368 support IDs, held for sample/isomer provenance), CHEMBL5737708 at NPT2a (521 support IDs, but confidence 8 and only 51 nonhit supports), CHEMBL5732233 at P2X2 (224 support IDs and a receptor-identity hold), and DYRK3 CHEMBL5363961 (231 support IDs, already used as the feasibility prototype). None is a new campaign-ready candidate.

The next search should prioritize unprofiled high-volume targets and assay catalogs for BACE1 and prothrombin. Their large target totals do not mean a single assay will be large enough: the currently observed BACE1 assay previews top out around a few dozen support IDs; the prothrombin previews include 94 for CHEMBL816079 and 66 for CHEMBL832832, all from incomplete target windows. These are reasons to count/list assays, not grounds to reject the whole targets.

## Budget and stop conditions

Use a new run directory and an explicit additional budget before online work. The first stage exposes the four top-ranked target choices and up to eight existing assay previews; each GLM decision chooses the next profile, assay count, metadata inspection, description read, source assessment, retrieval/curation step, or finish action. Cap new GLM decisions at 12 and new HTTP requests at 100. Report every attempted request, returned token count, failures, cache reuse, and exact coverage.

Stop the stage when one candidate reaches full assay curation and can be reviewed for a new freeze, or when the declared budget is exhausted. A numerical shortlist remains a review draft. It is not a frozen benchmark and cannot enter a campaign until source/sample identity, endpoint meaning, curation, the protocol version, and the label firewall are checked.

## Next deliverable

Produce a ranked target/assay queue, inspect the best-supported new assay candidates, and finish at least one complete curation if the public data support it. If none passes, retain the reject/hold/unknown reasons and state the searched scope. A new campaign is a later, separately frozen step.
