# D2-2: GLM expansion on the frozen DYRK3 feasibility pool

**Status: done, post-exposure retrospective analysis.** The 231-compound DYRK3 v1 pool, labels, 50-query budget (10 initialization + four batches of 10), prompt, model, numerical tools, and thresholds were unchanged. This is a feasibility pool, not a new benchmark or a test of generalization. The 10 GLM seed 0–4 runs were reused by hash; 30 new runs covered seeds 5–19 for bit and count. No seed or representation was pooled across arms.

The budget and [power declaration](d2_power_declaration.md) were locked at `2026-10-19T11:02:57.8747379Z`, before the first real D2-2 run at `2026-10-19T11:07:57.321262Z`. Their SHA-256 values are in [the declaration lock](pre_real_declarations_lock.json). The frozen prompt and request-configuration source files matched v1 byte for byte; the synthetic-only probe succeeded. The preflight [manifest](d2_preflight/MANIFEST.json) has SHA-256 `cce3b4eca1a4e83701ae404847db27fd39a55a8577b665e20db1b3764ca35513`.

The primary outcome is H@50, the number of measured hits among 50 distinct queried compounds. Values below are mean paired differences across 20 identical seeds, with 10,000 paired bootstrap resamples (seed 20261018). bit is the primary representation; count is a separate sensitivity analysis.

| GLM minus comparator | bit, mean [95% interval] | count, mean [95% interval] | Interpretation |
|---|---:|---:|---|
| `structure_prior` | **+1.70 [0.30, 3.10]** | −0.10 [−1.65, 1.35] | A bit-only difference is observed against a label-free structural ranking. |
| fixed greedy | **0.00 [−1.25, 1.25]** | −0.40 [−1.50, 0.75] | No evidence that GLM policy choice improves on the prescribed feedback-driven controller. |
| label shuffle | +2.15 [−0.50, 4.50] | +2.55 [0.20, 4.95] | Secondary feedback diagnostic; representation-specific. |
| `matched_proportion` | +0.75 [−0.05, 1.50] | −0.45 [−1.30, 0.35] | No clear gain over a no-LLM policy mix with a comparable diverse-policy fraction. |

Mean GLM H@50 was 29.25 (bit) and 28.90 (count). Mean cumulative hits at 10/20/30/40/50 queries were 4.65/10.50/16.80/22.55/29.25 for bit and 4.65/10.25/16.25/22.45/28.90 for count. The 10–50 average cumulative-hit values were 16.70 and 16.43. The mean query position of the first hit was 1.75 for both. Relative to the full-pool random expectation of 50 × 116/231 ≈ 25.11 hits, the enrichment factors were 1.165 and 1.151. These descriptive values do not isolate agentic control.

Across 80 decisions per representation, GLM selected `knn_diverse` 49 times, greedy 30 times, and random once for bit; for count, diverse 48 and greedy 32. After a previous batch with 1–2 hits, bit chose diverse once and random once (2 decisions); count chose diverse 4/4 times. With 3–5 prior hits, bit chose diverse 29/34 and count 20/30. With 6+ prior hits, bit chose diverse 19/44 and count 24/46. There were **zero** prior-batch zero-hit decisions, so whether GLM switches strategy after zero hits cannot be estimated here (denominator 0). The new bit seeds were diverse-dominant in 4/15 trajectories, compared with 4/5 old bit seeds; count was 10/15 new versus 0/5 old. Thus the new trajectories are not simply repeats of the old seeds' patterns. These conditional counts are observational and do not prove an effective feedback rule.

The separately locked `rule_adaptive_v2` control triggered for the first time in 10/20 bit and 14/20 count seeds, exactly matching its before-run target. Its H@50 difference from fixed greedy was −0.05 [−1.20, 1.00] on bit and 0.00 [−0.55, 0.40] on count. See [D2-1 summary](d2_1_summary.md) for its independent comparisons. D1's older `rule_adaptive` name denotes `rule_adaptive_v1`.

## Cost, failures, and interpretation

The 30 new runs used **120/120 successful GLM decisions**, exactly 120 HTTP attempts and 120 returned request IDs; no retry or failure event occurred. Returned usage was 285,146 prompt tokens and 6,781 completion tokens, including 682 reasoning tokens. Total model decision time including any waits was 210.69 s. Across the new runs, fingerprint feature construction took 0.65 s, numerical analysis 0.59 s, and numerical selection 3.89 s. Source-data acquisition time was not available from these frozen retrospective runs and is **unknown**. The reused seed 0–4 runs contain 40 completed decisions and 40 recorded HTTP attempts, with 97,956 prompt and 2,551 completion tokens returned for those completed decisions; their two historical failure events are reported separately, and missing usage from failures is not imputed. Thus this study's 160 completed decision slots are not the same as the total number of historical attempts.

The [power declaration](d2_power_declaration.md) warned that the roughly +0.30 count-side space between the structure-only and fixed controls is smaller than the approximate 1.45-hit detectability scale. The count interval crossing zero is therefore an informative limitation, not a failed run. The bit GLM advantage over `structure_prior` is consistent with using revealed labels through the shared kNN tools; it **does not show extra value from GLM control**, because fixed greedy reached the same mean H@50. Multiple primary intervals were examined without multiplicity adjustment; these retrospective intervals should not be read as a broad efficacy claim.

The zero-hit fallback module passed 14 synthetic tests, while its real-data path was not exercised: across the 280 R5 control runs, fallback batches totaled 0 and the smallest initialization hit count was 1. In the current 20-seed GLM cohort, no initialization had zero hits. The code-path check is not a real low-prevalence validation; that requires a different, scientifically qualified pool.

## Appendix: random reference

GLM minus uniform random was +4.45 [3.00, 5.90] on bit and +4.10 [2.20, 6.15] on count. This comparison is secondary because random selection lacks the label-free structure ranking available to the primary floor.

The 89 protected frozen/source/evidence files matched their pre-run hashes after analysis. Compound-level trajectories and [the private analysis manifest](../d2_glm_private_20261019/MANIFEST.json) remain excluded from Git; the private manifest SHA-256 is `a7a786b8219a77b09d3742dbb3602d14103f49291e8b061e2b4365b2022d65b5`. The first D2-1 attempt remains recorded as blocked; only the explicitly authorized second attempt is marked done.
