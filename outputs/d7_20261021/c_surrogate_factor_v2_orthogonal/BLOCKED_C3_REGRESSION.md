# C3-v2 Tier B stop: locked one-class fallback conflicts with D5 regression

Date: 2026-10-21 UTC. This is a post-exposure implementation check, not a new
benchmark or campaign. No C3 matrix or C4 GLM calls were run.

The additive six-proxy lock was written before scoring the new Morgan logistic
proxy (`C1_LOCK_v2.json`). The resulting six-proxy AUC/EF1 summary is
`C2_SIX_PUBLIC.json`; TNAP passes the two stated Tier B strength conditions.
The original four C1 definitions, their C2 metrics, and the prior Morgan-GBDT
C2 result were reused without modification.

Two specification conflicts emerged:

1. The task card says D5 `logreg_greedy` uses sklearn's default `max_iter=100`,
   but the frozen D5 implementation explicitly uses `max_iter=200` in
   `outputs/d5_20261020/e_menu/expanded_tools.py:_logreg`. The additive proxy
   copies the actual D5 value (200) to preserve the requested exact regression.
   This choice is explicit in `C1_SPEC_v2.md` and `C1_LOCK_v2.json`.
2. The same card requires **all six proxies** to use the locked C1 one-class
   fallback to `uniform_random`, and also requires exact reproduction of D5
   `knn_greedy` (TNAP bit 20-seed mean 20.35). The C1 source returns `None`
   for any one-class observation set, including `S_incumbent`. D5's frozen
   `NumericalTools.score_knn` still computes kNN scores in a one-class state
   and `knn_greedy` selects by those scores. These definitions cannot both
   produce the same selection trajectory.

The immutable, hash-verified D5 archive and the current public/private TNAP
pool were checked. Seed 5 has zero hits in its ten initialization queries.
At the **first feedback batch**, C1 requires random fallback while the D5
historical run used kNN greedy. Their **first selected compound already
differs**; details and all relevant hashes are in `C3_REGRESSION_GATE.json`.
The D5 historical H@50 for this seed is 6. This is a definition conflict, not
sampling noise. The remaining six regressions were not executed because the
task card says any one mismatch triggers a Tier B stop. There was no attempt
to change code or parameters to match the expected means after viewing this
result.

Before C3 can resume, the governing specification must choose one consistent
definition and set its regression expectations **before** new campaigns:

- Keep the locked C1 fallback for all six proxies. Treat the seven D5 means as
  historical comparisons, not exact requirements for cells affected by
  zero-hit states; preregister new expected behavior and a revised test.
- Create a new additive interface version exempting `S_incumbent` kNN from the
  one-class fallback so the D5 trajectory can be reproduced. This changes the
  cold-start rule and must be named and locked as a new version; the original
  C1 and historical results stay untouched.

Neither route has been silently selected. The full C3 CPU matrix and C4 GLM
arm remain stopped. CP-2 approval remains required for any future C4 calls.
