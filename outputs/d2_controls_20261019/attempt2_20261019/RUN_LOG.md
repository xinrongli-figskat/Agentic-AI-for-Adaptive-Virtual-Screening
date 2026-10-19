# D2-1 second attempt log

Attempt prepared UTC: 2026-10-19T10:53:28.5463623Z
First blocked attempt preserved; see ../BLOCKER.md
User-authorized repair: synthetic test entry path only; output path redirected
Locked rule SHA-256: 6d7d54a8ae84a53916f151c74249451d486993ccd6e7814818c1d18df126951a
Attempt code SHA-256: 9340ca7337681573fff3d77d0fbccfab438c50a56431a98564a7a81b48b5b1a6
GLM calls before attempt: 0

Attempt completed UTC: 2026-10-19 (see private RUN_LOG.md for exact timestamps).
Validation: three D2-1 unit tests passed; 280 existing R5 rows recomputed identically; 20 frozen fixed/random runs replayed exactly; synthetic oracle and label-shuffle boundary checks passed.
First-trigger target matched: bit 10/20 (batch 3: 6; batch 4: 4); count 14/20 (batch 2: 2; batch 3: 7; batch 4: 5).
Private output MANIFEST SHA-256: 3cb895e3fe9a18ddfc17d91564cd0103febc90861e13d4f139e03328011b40ac.
No GLM calls were made in D2-1. D2-2 remains subject to its separate preflight gates.

D2-2 preflight: frozen prompt/request modules byte-identical; ten old GLM run hashes matched; one synthetic-only probe succeeded. Preflight MANIFEST SHA-256: cce3b4eca1a4e83701ae404847db27fd39a55a8577b665e20db1b3764ca35513.
Budget and power declaration lock UTC: 2026-10-19T11:02:57.8747379Z. First real D2-2 run UTC: 2026-10-19T11:07:57.321262Z.
D2-2 completed: 30 new runs, 120/120 successful GLM decisions, 120 HTTP attempts, 0 new failure events. Old seed 0–4 runs referenced read-only. 89 protected files unchanged. Private GLM MANIFEST SHA-256: a7a786b8219a77b09d3742dbb3602d14103f49291e8b061e2b4365b2022d65b5.
The count result is a separate sensitivity analysis; GLM advantage over fixed greedy was not established in either representation. See d2_summary.md.
Independent D2-3 check repeated after analysis: 14 low-hit fallback synthetic tests passed on remote Python 3.10; this does not imply the zero-hit branch ran on real DYRK3 data.
