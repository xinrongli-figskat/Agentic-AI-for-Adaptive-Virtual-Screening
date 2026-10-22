# D3 TNAP cold-start decision (locked before D3-1)

Date: 2026-10-19. Post-exposure protocol decision. This document does not change the original low-hit fallback proposal or prior campaigns.

## Decision

Apply option A: remove the forced zero-hit fallback from every primary comparison arm. `fixed` already chooses `knn_greedy` regardless of observed hits. `fixed_schedule`, `rule_adaptive_v2`, `label_shuffle`, and other eligible arms follow only their declared policy rules, without a hidden zero-hit override. All arms share the same seed-specific initialization, 50-query budget, feedback times, numerical tools, and representation. A separate, explicitly named secondary arm, `forced_random_coldstart`, follows `fixed` except that it chooses `uniform_random` while the cumulative number of revealed hits is zero. Every fallback selection consumes the ordinary query budget; there is no redraw or free query. The arm returns to `knn_greedy` after the first revealed hit.

1. **Comparability:** The brief requires the same tools, initial information, and query budget. The prescribed `fixed` controller has no fallback. Giving only the new arms a fallback would break the paired comparison precisely on seeds where it activates.
2. **Disproven no-information premise:** All observed nonhits still carry information. Greedy kNN already favors compounds dissimilar to observed nonhits; it does not become signal-free.
3. **Auditability:** Without an implicit conditional override, compared arms differ only in their declared strategy rules. The original fallback is retained as a measured secondary arm.

## Derivation and regression target

The existing `NumericalTools.score_knn` uses `base=(1+sum(y))/(2+n)` and `score=(2*base+sum(w*y))/(2+sum(w))`, with at most five nearest revealed compounds and `w=Tanimoto**2`. If all `n=10` revealed labels are zero, `base=1/12`, so `score=(1/6)/(2+sum(w))`. Its derivative with respect to `sum(w)` is negative. `knn_greedy` maximizes score, so it selects a candidate with the smallest summed similarity weight (subject to the locked seeded tie rule). Examples: sum(w)=0.2 gives 0.0758; 1.0 gives 0.0556; 2.0 gives 0.0417; 4.0 gives 0.0278.

For TNAP's provisional N=462 and K=53, exact hypergeometric P(no hit in 10)=0.29191094238049553, hence about 5.8 of 20 seeds are expected to start with zero hits. This is a prospective expectation, not observed seeds. The synthetic unit test must verify the score ordering and greedy choice against the existing numerical code before any TNAP data check.
