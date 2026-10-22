# C3 CPU matrix specification — additive post-exposure version, 2026-10-21

Prerequisites: `C2_SIX_PUBLIC.json` TNAP strength gate passes; the seven
versioned checks in `C3_REVISED_REGRESSIONS.json` pass. Preserve the original
failed seven-mean assertion and the v3 checker mistake as separate evidence.

Use TNAP and DYRK3 frozen pools, bit fingerprints, seeds 0–19, 50 queries
including the common ten-query label-blind initialization and four ten-query
feedback batches. The six proxies are fixed by C1 v1 and additive C1 v2.
At every feedback point, fit on revealed outcomes only. One-class means
frozen random fallback, with all selections charged to the budget.

Strategies are the six orthogonal actions in `C3_REGRESSION_ADDENDUM_v3.md`.
The four always-run proxy-dependent fixed policies are greedy, diverse,
persistent_random_until_first_hit, and diverse_random_coldstart. Three
metacontrollers (Thompson Beta(1,1), UCB1, uniform random-mixture) select from
the complete six-action menu at a fixed proxy; their feedback reward is new
hits divided by ten queries. A persistent-random choice at zero hits is
committed until a hit is observed, as in D5. Pure random runs once per pool
and seed, then is reused in all six proxy columns as `surrogate_invariant`.
The random-mixture policy draw is SHA256(`c3mix|seed|round`) modulo six, so its
nominal policy sequence is shared across proxy cells until commitment differs.

ENS uses the same 64+64 candidate shortlist for every executed column. A
public-structure, synthetic-outcome timing probe measured 37.84 seconds for
Morgan GBDT and 31.04 seconds for 217-descriptor GBDT, both above the
predeclared five-second per-decision feasibility threshold. Therefore ENS is
**not run for either GBDT column**. No reduced-list GBDT ENS is allowed.
ENS is run for the other four proxy columns. This gives 1,680
proxy-dependent regular/meta campaigns, 160 ENS campaigns, and 40 unique
random campaigns, for 1,880 unique CPU campaigns and zero GLM calls.

Analysis uses 20 seed-paired H@50 results per cell. To keep the six proxy
columns comparable despite omitted GBDT ENS, primary `spread_nontrivial`
uses the **four common nonrandom fixed policies**. It is the range of their
20-seed mean H@50 values. A 10,000-resample paired seed bootstrap (seed
20261018) recomputes the range in every resample. ENS-inclusive spread is
reported separately for the four eligible proxy columns and is never mixed
into the six-proxy trend. `adaptive_gap` is best common fixed mean minus
best of the three meta-controller means in the same proxy cell. `random_floor`
reports the one empirical random H@50 mean per pool and analytic 50*K/N.
Trend analysis uses TNAP's six *previously locked* observed AUC values;
report Spearman correlation and six paired points descriptively, not as a
causal effect or a model-selection criterion. DYRK3 is a CPU negative control.

All individual labels, selections, and trajectories are written only under
`c_surrogate_factor_v2_orthogonal_private` (gitignored). Public files hold
aggregates and source hashes. No remote 4090 or GPU is used. C4 remains
outside this CPU specification and requires CP-2 authorization after the
gate assessment.
