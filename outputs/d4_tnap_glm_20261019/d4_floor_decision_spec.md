# D4-0: TNAP prescribed-controller floor decision

Date: 2026-10-19 UTC. This is a **post-D3, pre-GLM** decision. It does not rewrite the frozen TNAP pool, D3 protocol, CPU trajectories or their conclusions. D3 bit outcomes are known; the new GLM arm has not run.

In six shared, unlabeled zero-hit initialization seeds (5, 6, 15, 17, 18, 19), `fixed` found 6.17 hits by query 50 on average, while `forced_random_coldstart` found 24.33. In the other 14 seeds the two arms used the same policy and obtained the same per-seed outcome; their overall means were 20.35 and 25.80, respectively. D3's paired forced-minus-fixed difference was +5.45 with a 95% paired-bootstrap percentile interval [1.85, 9.55]. The `fixed` bit arm had one run out of 20 with no hit by query 50 (seed 18); **four right-censored first-hit runs occurred across all 280 D3 runs**, not four in `fixed`. The task-card wording conflated these denominators; this correction changes no decision.

When all observed labels are nonhits, the existing score is `2×base/(2+sum(w))`, strictly decreasing in the summed similarity weight. `knn_greedy` therefore chooses candidates least similar to observed nonhits. This is a deterministic novelty preference, but on the TNAP pool it frequently bypassed hit-rich regions and produced poor cold-start results. The mechanism is a plausible interpretation of the trajectory difference, not a causal proof that the same behavior will occur in other pools.

**Main prescribed controller for D4 is `forced_random_coldstart`; `fixed` remains a secondary, known-weakened variant.** This choice is made before any TNAP GLM result. Reasons:

1. The brief asks for the incremental contribution of agentic control against a well-specified prescribed controller. D3 shows `fixed` is strongly disadvantaged by its zero-hit behavior on TNAP; using it as the only main floor would inflate apparent GLM benefit.
2. GLM may choose `uniform_random`, but the original `FixedController` structurally cannot. Comparing GLM only to `fixed` would hand GLM an approximately +5.45 mean-hit opportunity from the cold-start branch alone, without establishing superior reasoning.
3. `forced_random_coldstart` is fully predetermined, uses no LLM, and spends the same 50-query budget. It is a valid prescribed controller. The original `fixed` remains visible as a secondary comparison with this limitation stated.

All D4 arms retain the shared seed-specific 10-query unlabeled initialization, 4×10 feedback batches, bit/count tools, 1000 nM labels, and 50-query budget. **The GLM arm itself gets no forced fallback:** it must select a policy at every feedback point from the unchanged v1 menu. This isolates whether its decision authority handles the six cold-start seeds. No prompt, request parameter or TNAP frozen file may be changed to favor the new floor.
