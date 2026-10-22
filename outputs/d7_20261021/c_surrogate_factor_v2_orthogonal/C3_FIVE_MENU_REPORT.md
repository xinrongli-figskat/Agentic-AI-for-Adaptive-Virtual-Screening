# C3 five-policy correction: completed CPU comparison

Date: 2026-10-21 UTC. **Post-exposure descriptive analysis.** This report corrects the meta-controller menu mismatch discovered after the original 1,880-run C3 matrix. It does not create a benchmark, change the frozen TNAP or DYRK3 data, or rewrite the earlier six-policy trajectories, lock, deviation, and summary.

The five-action specification and runner were hashed at `2026-10-21T14:39:32.535388+00:00`, before any corrected result. All six surrogates on both pools then used the same menu: greedy, diverse, random, persistent random until first hit, and diverse with random cold start. The old fixed ENS results, where present, remain historical and are not a choice available to the corrected meta-controllers. The original four common fixed arms and pure-random reference were reused from the hash-verified C3 summary. No GLM request was made.

The synthetic-label preflight passed: changing unrevealed synthetic outcomes did not change the first decision or selected IDs for any of the three meta-controllers. The 720 corrected CPU campaigns finished in about 111 seconds. The private trajectory audit checked every run against the frozen labels and label-blind initialization: five stages, 50 distinct queries, 20 seeds per cell, no out-of-menu decisions, **zero ENS decisions**, and **zero GLM calls**. All checks passed. The corrected trajectories are in a separate ignored private directory.

`adaptive_gap` below is the best mean H@50 among the unchanged common fixed arms **minus** the best mean H@50 among the three corrected five-menu meta-controllers. A positive value means the best fixed arm found more hits on average. The comparison is descriptive, with 20 seeds per arm and no claim of causal or cross-target generalization.

| Proxy | TNAP AUC | TNAP fixed − meta H@50 | DYRK3 fixed − meta H@50 |
|---|---:|---:|---:|
| S_weak | 0.771 | 2.15 | 0.70 |
| S_morgan_gbdt | 0.803 | 4.70 | 1.15 |
| S_strong | 0.821 | 3.50 | 0.65 |
| S_morgan_logreg | 0.844 | 2.15 | 0.35 |
| S_maccs | 0.864 | 1.95 | 0.50 |
| S_incumbent | 0.897 | 2.20 | 0.05 |

Across the six TNAP proxy points, Spearman correlation between measured AUC and corrected `adaptive_gap` is **−0.20**. The original six-menu value was +0.257; that historical number is not the common-menu result and should not be used for the present comparison. Six selected, post-exposure points cannot establish a trend or a mechanism. The fixed-policy spread and bootstrap intervals are unchanged; under the earlier C4 cell gate, `S_strong` remains the only eligible TNAP proxy. DYRK3 remains a CPU negative control under the prior pool-level gate.

The five names do not imply five distinct behaviors in every state. With the authorized one-class random fallback, `greedy` can coincide with `persistent_random_until_first_hit`, and `diverse` with `diverse_random_coldstart`. In those states, the nominally uniform random mixture gives 40% weight to each of the two paired behaviors and 20% to random. This was kept fixed for all six proxies; it limits interpretation of policy diversity. Meta-controller choices are also affected by seed-specific stochasticity and only four feedback rounds.

This completes the **CPU correction only**. Any C4 GLM arm still requires CP-2 authorization and a five-action GLM protocol lock before calls. Old D5/D7 comparisons remain their own versioned experiments; a new five-menu GLM result would not be directly interchangeable with those earlier menus.

Files: `C3_FIVE_MENU_SPEC_v1.md`, `C3_FIVE_MENU_LOCK_v1.json`, `run_meta_five.py`, `C3_FIVE_SYNTHETIC_PREFLIGHT.json`, `C3_FIVE_PROGRESS.json`, `C3_FIVE_AUDIT.json`, `C3_FIVE_PUBLIC_SUMMARY.json`. The run files remain under `outputs/d7_20261021/c_surrogate_factor_v2_orthogonal_five_private/runs/` and contain labels; do not publish them.
