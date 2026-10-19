# D2-1 second attempt, post-exposure control

The user-authorized repair changed only the synthetic test invocation and redirected this attempt's output paths. The first blocked attempt remains unchanged. The scientific rule was locked before results at SHA-256 `6d7d54a8ae84a53916f151c74249451d486993ccd6e7814818c1d18df126951a` (2026-10-19 10:21:33 UTC).

All 280 existing R5 control rows recomputed identically; the 20 frozen fixed/random seed 0–4 runs replayed exactly. Synthetic oracle boundary and label-shuffle separation checks passed. The predicted first-trigger counts and rounds matched: bit 10/20 (batch 3: 6; batch 4: 4), count 14/20 (batch 2: 2; batch 3: 7; batch 4: 5). Bit never triggered at batch 2, as predeclared.

Paired H@50 difference for `rule_adaptive_v2 − structure_prior`: bit +1.65 [0.25, 2.95], count +0.30 [−1.20, 1.80] across 20 seeds. Relative to the fixed greedy controller: bit −0.05 [−1.20, 1.00], count 0.00 [−0.55, 0.40]. These are retrospective findings on the already exposed DYRK3 feasibility pool and do not establish a generalizable agent benefit. Count is a separate sensitivity representation.

Compound-level trajectories, paired rows, regression evidence and their hash manifest are stored only in `d2_rule_adaptive_private_20261019/` and excluded from Git. No GLM call was made in D2-1. The D1 files called `rule_adaptive` correspond to `rule_adaptive_v1`; this attempt's new arm is `rule_adaptive_v2`.
