# C3-v2 orthogonal regression addendum v3 — 2026-10-21

This is a post-exposure successor to the blocked seven-mean regression. The
user chose to **retain the locked C1 one-class random fallback**. The failed
original regression and its evidence remain untouched. This addendum must be
hashed before new C3 campaigns. D5 outputs remain historical comparisons.

For TNAP bit, seeds 0–19, 50 total queries (10 label-blind initialization,
four feedback batches of 10), all candidate pools and labels remain frozen.
No hidden label is available to the surrogate or selector before an oracle
query. A one-class state makes every surrogate score return `None`, and the
next batch uses frozen `uniform_random`; those queries spend the normal budget.

Seven revised backward-compatibility checks, all on complete trajectories:

1. `greedy × S_incumbent` equals historical D5
   `persistent_random_until_first_hit` for all 20 seeds. The original D5
   greedy mean 20.35 is **not** a valid expectation under C1 fallback.
2. `diverse × S_incumbent` equals historical D5
   `diverse_random_coldstart` for all 20 seeds. The original D5 diverse mean
   18.45 is a historical result, not a C1-fallback expectation.
3. `random` equals historical D5 `uniform_random` for all 20 seeds and is
   surrogate-invariant.
4. `persistent_random_until_first_hit × S_incumbent` equals its D5 namesake.
5. `diverse_random_coldstart × S_incumbent` equals its D5 namesake.
6. `greedy × S_morgan_logreg` equals D5 `logreg_greedy`, including its
   explicit `max_iter=200` and one-class random fallback.
7. `ens_one_step_proxy × S_incumbent`: on seeds with both classes after
   initialization, equal the D5 ENS trajectory. On zero-hit seeds, use
   frozen random for each one-class feedback state; once both classes are
   observed, use the unchanged D5 ENS function. Assert these transitions and
   50 distinct queries, but do not invent a historical H@50 target for the
   altered trajectory.

Each comparison checks selected compound keys and revealed outcomes at every
batch, not only means. A mismatch stops before the full C3 matrix, with the
first divergent seed and stage recorded. Historical D5 means remain 20.35,
18.45, 6.00, 25.80, 24.05, 25.80, 25.80 in the original order.

C3 factor design after the gate: six fixed surrogates, six orthogonal
strategies (`greedy`, `diverse`, `random`, `persistent_random_until_first_hit`,
`diverse_random_coldstart`, `ens_one_step_proxy`), plus Thompson, UCB1, and
random-mixture metacontrollers over that six-strategy menu. Random runs once
per pool and seed and is reused across surrogate cells. The four new-model
cells and D5 legacy cells are never overwritten. ENS uses 64 top-probability
+ 64 top-information candidates for every surrogate. If measured GBDT
refitting makes this infeasible, skip ENS for both GBDT columns and record the
timing; never silently shrink the shortlist.

Private per-compound trajectories stay in an ignored directory. Public C3
analysis may contain only aggregates. Paired bootstrap uses seed 20261018.
No C4 GLM calls are included. The separate CP-2 approval is required before
any eligible LLM cell begins.
