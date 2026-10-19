# D2-1 rule_adaptive_v2 specification

Date: 2026-10-19. Post-exposure control-arm repair on the frozen DYRK3 v1 pool. This specification is locked **before** any v2 arm result is calculated. It does not change the frozen benchmark, v1 runs, existing R5 arms or their outputs. Brief: compare greedy and diversity-aware policies and make decisions responsive to each campaign's revealed evidence.

## Rule and decision-point mapping

The shared budget remains 10 unlabeled initialization queries followed by four 10-query feedback batches, with no repeated compound. Let `h_0` be the number of hits revealed in initialization and `h_r` the number newly revealed in feedback batch `r`, for `r=1..4`. The next decision uses only outcomes already revealed in **that** campaign:

| Upcoming feedback batch | Previous batch index `r` | Available comparison | Policy |
|---|---:|---|---|
| 1 | 0 | Only initialization exists | Force `knn_greedy` |
| 2 | 1 | Compare `h_1` with `mean(h_0)` | `knn_diverse` iff `h_1 < mean(h_0)`, else `knn_greedy` |
| 3 | 2 | Compare `h_2` with `mean(h_0,h_1)` | Same strict-inequality rule |
| 4 | 3 | Compare `h_3` with `mean(h_0,h_1,h_2)` | Same strict-inequality rule |

The policy is diverse only when the most recent batch's realized yield has fallen below the campaign's earlier mean. It contains no fixed prevalence cutoff, so the condition can fire in pools with different hit rates. A decline in yield is consistent with exhausting one promising neighborhood, though it is not proof of that mechanism. The original `rule_adaptive` is retained unchanged and named `rule_adaptive_v1` in all **new** output tables; the new arm is `rule_adaptive_v2`. D1's older table uses `rule_adaptive` for v1 and is not edited.

The existing zero-positive cold-start fallback remains in force: if no hit has been revealed at a decision point, choose `uniform_random` until a hit appears; these queries spend the ordinary 50-query budget. It is a separate safety rule, not a changed definition of the v2 decline trigger. On DYRK3 the existing 20-seed run had at least one hit in every initialization, so this branch is expected to be unexercised by these real-data controls.

## Locked implementation check target

The existing R5 `fixed` arm's `cumulative_true` provides `h_0..h_4`. Before the **first** v2 trigger, its selections match fixed greedy, so first-trigger seeds and rounds can be predicted exactly from that fixed trajectory. The predictions to check against the new run are:

| Representation | First-trigger seeds | Upcoming batch distribution |
|---|---:|---|
| bit | 10/20 | batch 3: 6; batch 4: 4 |
| count | 14/20 | batch 2: 2; batch 3: 7; batch 4: 5 |

This is an implementation-correctness target, **not** a prediction that the strategy improves H@50. Mismatch blocks D2-2; do not adjust the rule after seeing the result. Later triggers cannot be predicted from fixed once a trajectory diverges. In bit, no seed is predicted to trigger at batch 2. The initialization yield `h_0` often lies below first greedy batch yield `h_1`, lowering the earlier mean; this is a property to report, not a reason to replace the predeclared rule.

## Inputs, outputs and comparison

Use the same frozen 231-compound pool, public bit/count Morgan features, seed-specific unlabeled initialization, kNN greedy/diverse numerical tools, 50-query budget and 1000 nM labels as v1. Run seeds 0–19 separately for bit and count. Preserve existing `rule_adaptive_v1`, `fixed`, `random` and all other R5 results. Report v2 trigger totals, per-batch counts, first-trigger seed/round match, paired H@50 against fixed and against the three D1 floors (`random`, `structure_prior`, `label_shuffle`) using 10,000 paired-seed bootstrap resamples, seed 20261018. This is post-exposure description, not a new campaign or a generalization claim.

## Required regression protection before GLM

1. Recompute fixed/random seeds 0–4 and match frozen v1 selections and H@50 exactly.
2. Recompute all seven existing R5 arms for both representations and seeds 0–19, matching `control_summary.csv` row by row, with no old output altered.
3. Rerun the existing synthetic oracle-boundary tests and a label-shuffle leakage test that demonstrates model-facing permuted labels while true-label evaluation stays separate.

Any failure is a **hard stop**: write `BLOCKER.md`, set `STATUS=blocked`, and do not start D2-2.
