# D7 disposition execution record — 2026-10-21

This is an additive, post-exposure record. It does not change frozen pools, labels, thresholds, prior strategy implementations, or any locked D3–D7 decision.

## B line and CP-1

The authorized physical-call cap was 380. The 20-seed × 5-repeat matrix is complete: 100/100 campaigns, each with 50 distinct queries. The line used 361 new physical HTTP requests: 360 valid model decisions and one malformed structured response retained from physical request 94. No new format failures, retries, or abandoned repeats occurred. The earlier malformed response remains counted as an invalid decision and physical call; the same decision point was successfully replayed during the authorized recovery. The original failed HTTP request body was not separately stored, so its prompt identity is supported by the locked old code/state and deterministic reconstruction hash, not by a historical byte-for-byte body comparison.

The pre-locked B2/B3 analysis reports pooled within-seed model SD 2.1943 H@50, model-noise SE 0.2194 for five repeats across 20 seeds, and a minimum of one repeat per seed to meet the pre-set SE ≤ 0.5 continuation criterion. B3 passes, so the variance condition for considering C’s LLM phase is met. Historical GLM-vs-control estimates remain descriptive and post-exposure; they do not establish a general agentic advantage. See [B_REPORT.md](b_model_variance/B_REPORT.md) and [B_ANALYSIS.json](b_model_variance/B_ANALYSIS.json).

The 380-call cap leaves 19 calls of tolerance beyond 360 valid decisions plus the already observed format failure. The one-replay-per-decision protocol was applied as authorized; there were no new failures requiring a replay. The report checkpoint is stage-based. CP-1 is satisfied by the B report; no C LLM call has been made.

## C local CPU work and hard stop

The local DYRK3 backup is field-sufficient for C-2/C-3. Its hash-verified public candidates provide `compound_key` and `standardized_smiles`; the private backup labels contain `compound_key` and `outcome` plus provenance fields, which can be projected to the required two fields. Public/private key agreement and manifest hashes were checked in the local-input audit. The pool used here is explicitly the backup copy, not a live remote freeze.

Before reading either pool’s labels, the C2 environment and descriptor names were recorded in `C2_ENV_LOCK.json`: Python 3.12.14, RDKit 2026.09.1, scikit-learn 1.9.1, SciPy 1.18.1, NumPy 2.5.4; 217 descriptors with descriptor-name SHA-256 `1f99f08c69f76b679316a7ea5cb57d6ac6bddf6e43ceea0fae88fd2b9e3ac0aa`. C1 implementation and pool inputs are separately hash-checked by the runner.

C2 completed on CPU. The pre-registered expected ROC-AUC order was `S_weak < S_maccs < S_incumbent < S_strong`; the task card’s Tier B stop applies if `S_strong` is below `S_incumbent` on either pool.

| Pool | S_weak | S_maccs | S_incumbent | S_strong | Strict order | Gate |
|---|---:|---:|---:|---:|---|---|
| TNAP (462 compounds; 53 hit, 409 nonhit) | 0.7711 | 0.8642 | 0.8971 | 0.8206 | Fail | Stop: strong < incumbent |
| DYRK3 backup (231 compounds; 116 hit, 115 nonhit) | 0.6793 | 0.6725 | 0.6627 | 0.6260 | Fail | Stop: strong < incumbent |

Both pools fail the strict order, and each independently meets the `S_strong < S_incumbent` stopping condition. Therefore C3’s 1,600 CPU campaigns and C4’s LLM arm were not run. This follows the pre-registered Tier B rule; the surrogate ranks were not relabeled after seeing results. The aggregate summary is [C2_PUBLIC_SUMMARY.json](c_surrogate_factor/C2_PUBLIC_SUMMARY.json). Per-compound outcomes and out-of-fold scores remain in the ignored private output directory.

All C computations performed so far were local CPU work. No GPU or remote workstation was used. The previously approval-rejected remote path was not retried or bypassed.

## A-4

A-4 is deferred as recommended. No candidate evidence packages were built and no A-4 LLM calls were made. It remains outside the conclusions from B and C.

## Resulting scope

B completes the model-variance measurement and passes its continuation-precision gate. C does not support proceeding to the more costly campaign comparison because its pre-registered surrogate-strength gate failed on both pools. These results do not create a benchmark or a new campaign, and they do not establish an additional benefit from agentic control.
