# D8 report: alignment with the advisor’s latest guidance

**Date:** 2026-10-22  
**Status:** post-exposure engineering and documentation work. No frozen pool or labels were changed, no new benchmark was created, and no active-search evaluation was run.

## Progress check

The D7-A, D7-B, D7-C2/C3, D7-E and C4 lines are complete according to their saved receipts. D7-D has a completed 62-row identity audit, but no additional set is campaign-ready. The release work remains blocked at A-5 because two tracked patent sample extracts contain per-record activity values. D8 did not perform any Git operation.

The Task 2 request ledger was 521 physical requests at D8 start. C4 had added 161 requests, and this task added one synthetic API request: **683 cumulative Task 2 requests**. The D8 request returned 47,598 prompt tokens and 85 completion tokens (47,683 total). C4 returned 101,988 tokens. Earlier Task 1 requests are outside this Task 2 ledger. No campaign decision was made during the D8 probe.

## Advisor-facing terminology and measurement effort

Created `GLOSSARY.md`, `SUMMARY_FOR_ADVISOR.md`, and `MEASUREMENT_EFFORT_NOTE.md`. The measurement-effort note defines the quantity as the number of independent concentration–response determinations recorded per tested compound in the source deposition. In TNAP, its median was 1 and maximum 21; it predicted the measured class with ROC-AUC 0.879, while the strongest single structural descriptor reached 0.598. This is consistent with selective follow-up of promising compounds, not a useful molecular feature, and it must be checked in other deposited screening datasets.

The advisor summary reports the current evidence cautiously: one source-limited evaluation set; no clear difference between the language-model controller and the best fixed rule selected after seeing results; higher point estimates against several adaptive baselines, with limitations on those comparisons; substantial response variability; and no systematic relation between the tested prediction methods’ ROC-AUC and the performance range among selection rules. Four of six method settings showed every tested adaptive controller below every fixed rule. This is evidence about these post-exposure experiments, not a general claim that adaptive control cannot help.

An automated case-insensitive scan of the two advisor-facing documents checked for the project’s listed internal shorthand, including `H@50`, `campaign`, `oracle`, `structure_prior`, `label_shuffle`, `adaptive_gap`, `knn_greedy`, `knn_diverse`, `ens_one_step_proxy`, Tier labels, and CP labels. Both documents passed with zero matches.

## Full-library visibility variant

Added a separate `llm_library_visible` implementation. It presents all 462 public candidate keys and standardized structures, plus one score or explicit null per candidate. It shows only outcomes already disclosed for selected compounds. The frozen controller and previous strategy implementations were not modified.

The three unit tests passed. A full-pool synthetic preflight also passed: the serialized candidate key/structure set equalled the public pool; synthetic changes to unselected outcomes changed neither the prompt nor controller decision; and no unselected outcome or pool-wide label statistic appeared in the payload. No hidden-label file was opened and the screening oracle was called zero times. The payload was 93,649 characters; the specified estimate was 23,413 tokens, below the 80,000-token limit.

One real provider request was made using only four synthetic revealed outcomes. It used `glm-5.3-flash`, `do_sample=false`, and returned request ID `2026102216131889a08a5c25bb4ab1`; the model selected `greedy`. This was an API and information-boundary probe only, not an active-search result. The provider reported 47,598 prompt tokens and 85 completion tokens.

The optional 40-request checkpoint was deferred. The mandatory synthetic probe established that the full library fits the recorded request budget and that unqueried measurements remain hidden. Forty full-library calls would add substantial cost and would require a separate controlled evaluation; they are not needed to verify the interface.

## Qualification criteria and candidate re-evaluation

The revised teaching-prototype rule retains safeguards that protect interpretation: measured nonhit coverage and diversity, the chance of a single-class initialization, cluster and scaffold limits, and the fraction of the pool queried. It allows endpoint or source documentation uncertainty to be reported as a limitation when the measured outcome remains definable and molecular identity is adequately supported. The association between measurement effort and outcome is now reported rather than used by itself as an admission veto. No relaxation establishes direct binding or fixes an unresolved compound identity.

The row-level re-evaluation includes all 62 numerically passing assays. The saved strict identity table has zero campaign-ready rows; the current source-limited TNAP set remains the one usable evaluation set. Two additional source-tier-1 entries are candidates for limited source review, but the saved evidence does not establish them as usable. The remaining 59 are not admitted because identity evidence remains unresolved. The requested top-five descriptive ordering by measured nonhit count times scaffold-bucket count is included in `QUALIFICATION_RELAXATION.md` and `relaxed_admission_62.csv`. These rankings do not admit a pool.

## Decoy options, BindingDB, and prediction methods

`DECOY_OPTIONS.md` compares five decoy types and recommends examining measured active compounds at related targets as a separately named selectivity comparison. It records that the structure-only and label-permutation checks must also be reported for measured active/nonhit sets. TNAP and DYRK3 values are cited in the file.

`BINDINGDB_AS_FILTER.md` records the proposed use of BindingDB inclusion as a manual-review ranking signal, not an automatic admission rule. A complete independent BindingDB cross-reference was not verified locally. `SURROGATE_SCOPE_NOTE.md` freezes the current six prediction methods for this month and corrects the Boltz description: Boltz has a dedicated affinity module; its exclusion, along with Protenix, is due to time and incomplete contamination review, not a methodological rejection.

## Boundaries

This work did not change a threshold, modify a previous decision, create a new frozen set, launch a campaign, or touch Git. All D8 analyses are post-exposure. The only new provider use was the one synthetic probe described above. The optional 40-request checkpoint is the only deferred item; items 1–6 were otherwise completed as documentation, audit, or offline computation.
