# D2 hard stop: synthetic oracle test did not load

**Status:** `blocked` on 2026-10-19 10:24:32 UTC. D2-2 did not start; **GLM calls 0/120**. No new `rule_adaptive_v2` outcome was produced. This block follows the attached task card's rule: a D2-4 regression-protection failure is a hard stop and must not be repaired and continued autonomously.

The D2-1 rule was locked at 10:21:33 UTC, SHA-256 `6d7d54a8ae84a53916f151c74249451d486993ccd6e7814818c1d18df126951a`. Four decision-point unit tests (3 tests covering all four points) passed before the large run. The existing fixed trajectories yielded the locked **predictions** of first-trigger distributions: bit 10/20 (batch 3: 6, batch 4: 4); count 14/20 (batch 2: 2, batch 3: 7, batch 4: 5). These are **not observed v2 results**.

During the remote D2-1 run, the program progressed through 280 old-arm replay comparisons and 20 exact v1 fixed/random checks, then stopped at the synthetic oracle-boundary test. Its test invocation was:

```text
.venv/bin/python -B -m unittest oracle_boundary_v0.test_oracle_boundary
```

That test file imports `oracle_boundary` as a top-level module. Invoking it from the project root by module name did not put `oracle_boundary_v0/` on the Python import path, so test discovery failed with `ModuleNotFoundError: No module named 'oracle_boundary'`. This is a **test-entry/import-path failure**, not evidence that the oracle boundary itself leaked labels; nevertheless the required regression protection is **not passed**. The exact traceback is preserved in the private `d2_rule_adaptive_private_20261019/BLOCKER.md`.

The stopped run produced a prediction file and an empty `runs/` directory. It made no GLM request. Frozen manifest, R5 summary, campaign core/numerical tools and D1 manifest hashes match their previously recorded values. No frozen protocol or existing result was modified.

**Human decision required:** approve a new, separately logged attempt that corrects only the D2-4 test entry point (for example, run the existing test file from its own directory or set the import path). Before resuming, preserve this blocked run unchanged and create a new attempt directory or deviation record. Then rerun all D2-1 tests and locked first-trigger checks. D2-2 remains disallowed until the complete D2-1 and D2-4 acceptance conditions pass.
