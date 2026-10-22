# D7-C v2 progress report — 2026-10-21

Post-exposure retrospective work only. C v1 artifacts and outcomes remain unchanged. No new benchmark, pool, label threshold, campaign-ready claim, remote execution, GPU work, or GLM call was made.

## C6-v2 corrections

The three corrections are recorded in `CORRECTIONS_20261021.md`: D6's 4.20 was the SD of two-run differences rather than a single-run model SD; first-round agreement is 0.615 across 200 matched-summary pairs (38.5% disagreement), while later rounds are state-divergent; and C v1's assumed ordering/hard stop was a task-card design flaw, while execution correctly stopped without relabeling. Historical records remain intact.

The D7-B estimate used here is `SD_model = 2.1943108257491692`. It is the measured within-seed model SD, not D6's 4.20.

## C5-v2 repeated-GLM comparison

For each of 20 TNAP-bit seeds, the GLM H@50 is averaged over its five completed repetitions and paired against the corresponding four-feedback-decision D7-A bandit run. A 10,000-resample paired-seed bootstrap with seed 20261018 gives:

| Contrast | Mean GLM H@50 | Mean bandit H@50 | GLM minus bandit, 95% paired bootstrap interval |
|---|---:|---:|---:|
| Thompson | 25.32 | 20.55 | +4.77 [1.88, 7.93] |
| UCB1 | 25.32 | 17.00 | +8.32 [4.74, 12.12] |

These are post-exposure, TNAP-bit-only descriptive comparisons. The UCB1 implementation has only four decisions for a seven-item menu and is close to a strawman; Thompson is the more credible bandit comparison. Count-format comparisons remain on their earlier single-run/variance-component basis and are not mixed with these estimates.

## C2-v2 fifth proxy and observed ranking

The new proxy uses the exact same Morgan radius-2, 2048-bit, chirality-aware fingerprints as the incumbent, with the same gradient-boosting hyperparameters as C v1 `S_strong`: 200 estimators, depth 3, learning rate 0.1, random state 0. The environment and feature-spec lock was written before calculating this proxy's label-dependent score. Runtime versions matched the prior C2 environment lock: Python 3.12.14, RDKit 2026.09.1, scikit-learn 1.9.1, SciPy 1.18.1, NumPy 2.5.4.

One provenance deviation is recorded in `DEVIATION_C2V2_CODE_LOCK.md`: the canonical feature/model/CV specification and inputs were locked before the new fit, but the runner's own hash was not in that lock, and its aggregate-only output projection was edited after lock but before the fit. The scoring algorithm was unchanged by that serialization edit. The runner's final hash is in the C v2 manifest; it is not claimed to be a pre-result code hash.

Observed ROC-AUC order, fixed before any C3 campaign:

| Pool | Measured AUC order, low to high | AUC span | C2-v2 Tier B |
|---|---|---:|---|
| TNAP | S_weak 0.7711 < S_morgan_gbdt 0.8034 < S_strong 0.8206 < S_maccs 0.8642 < S_incumbent 0.8971 | 0.1260 | Pass: span ≥0.05; Morgan-GBDT is not >0.15 outside prior range |
| DYRK3 backup | S_strong 0.6260 < S_incumbent 0.6627 < S_maccs 0.6725 < S_weak 0.6793 < S_morgan_gbdt 0.7214 | 0.0954 | CPU negative control only; excluded from the TNAP factor conclusion |

For the TNAP pool, the fifth model's AUC lies within the four-model reference range, so neither C2-v2 stop condition is triggered. These ROC-AUCs use frozen-pool labels but no campaign outcomes; the observed rank was locked before C3. The five models cover only about 0.77–0.90 AUC on TNAP, so five points support trend direction only, not a fitted relationship.

## C3 not yet started: one method-definition decision is needed

The card specifies a 2-pool × 5-surrogate × 20-seed × 10-arm matrix, and says to refit the selected surrogate after each feedback batch. It also says the ten arms reuse D7-A's six nontrivial fixed policies. Those D7-A policies embed different predictors: kNN, logistic regression, and an ENS proxy. The card does not state whether C3 should replace those embedded predictors with the cell's selected surrogate, or preserve them unchanged. Preserving them means several arms ignore the surrogate factor; replacing them changes the frozen D7-A arm definitions. Either choice changes the meaning of the proposed factor experiment.

No C3 configuration was therefore locked and no C3 campaign was run. Once the model-to-arm mapping is resolved, the remaining pre-registered analysis is `spread_nontrivial` with paired-bootstrap interval, `spread_paired_mean` for comparison only, `adaptive_gap`, and observed versus analytical random floor. C4 still requires the separate CP-2 authorization before any LLM call; CP-3 is required before a second eligible LLM cell.

## Preserved limits

DYRK3 remains a signal-poor CPU negative control and cannot change TNAP conclusions. No new campaign-ready pool was created. C work to date used the local CPU, with the DYRK3 hash-verified backup, not the remote workstation or GPU. The previously approval-rejected path was not retried or bypassed. A-4 remains deferred.
