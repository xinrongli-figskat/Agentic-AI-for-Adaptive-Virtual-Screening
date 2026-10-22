# Homogeneity rule v2 for deposited dose-response assays

Date: 2026-10-19. Definition-level revision, post-exposure. Apply to all subsequently reviewed deposited dose-response assays, including PubChem BioAssay, without a TNAP-only exception. Lock this text and its SHA-256/UTC before calculating v2 results. The first D3-1 assertion and blocker remain unchanged.

## Mandatory gates

H1: Every original row must contain the same chosen qualifier tid and numeric endpoint tid, with the expected names in the deposited assay schema. Presence alone is insufficient for H2.

H2: Independently align every ChEMBL activity to a source row by SID and verify its relation and nM numeric value against the chosen source qualifier and endpoint values (convert source µM to nM). Every aligned activity must have the selected endpoint as its value source; no activity may draw from any other tid. Verify 1:1 coverage and source receipt hashes.

H3: Classify all auxiliary tid *names*, not just IDs, and verify their scope against the deposited assay description and target metadata. Permitted families are dose-point percent inhibition, per-range IC50 fit and qualifier, per-range fit quality (including standard error and Hill slope), and points excluded from the same fits. Every auxiliary name must match one of these families; any independent endpoint, target, counter-screen, cytotoxicity or separate protocol causes failure. One assay ID by itself does not prove this gate. Report family tid counts and minimum/maximum row coverage. Unknown names fail rather than being silently accepted.

## Required records, not gates

H4: Per source row, report auxiliary tid count and apparent underlying IC50 fit count (distinct per-range IC50 numeric columns). Distinguish single-fit from multi-fit rows and say when this is a proxy rather than verified replicate count. If depth varies, record measurement-precision heterogeneity in the pool card and D3 conclusion.

H5: Associate auxiliary tid count with the independently curated binary label using ROC-AUC and point-biserial correlation, computed only in a private evaluation stage. This diagnostic does not determine pool acceptance.

H6: For curated, usable compounds with any exact source measurement in [800,1250] nM, report compound key and underlying fit-count distribution in a private artifact; publish only aggregate counts. A censored bound is not treated as an exact near-threshold value.

H1-H3 must all pass before D3-2. H4-H6 must be reported even when they show limitations. This rule corrects the first card's literal `no_other_tid_present` test; the correction is recorded separately as a deviation, and the first failed result is retained.
