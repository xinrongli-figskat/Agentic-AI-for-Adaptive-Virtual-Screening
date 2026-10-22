# D10 run log

- 2026-10-22T14:45:43.704009+00:00 — Locked the D10 protocol, runner and D9 reference hashes before control results; `D10_LOCK.json` SHA-256 `72dd56c221287d0b08be42597063fa82541df8fe9c626c856768c189e24b91f8`.
- 2026-10-22T14:46:33.940635+00:00 — CPU comparator completed and wrote `D10_D9_MATCHED_MIX.json`; 20 seeds, two exact full-trajectory replays, all D9 initializations matched, 50 unique queries per seed, 10,000 paired bootstrap resamples. Result 12.85 mixture versus 14.25 D9; difference +1.40, interval [−0.40, +3.25]. CPU time including replay 39.12 seconds. No GLM calls.
- 2026-10-22T14:48:49.959510+00:00 — Completed and then refined the English advisor summary to state the finite-draw and fallback discrepancy explicitly; v1/v2 remained untouched.
- 2026-10-22 — Built a path-and-SHA evidence index and D10 closeout report. D3–D9, frozen inputs and Git were not edited.
- 2026-10-22T14:50:06+00:00 — Final verifier rechecked the D10 lock, all 20 saved private runs, every 50-query trajectory and D9-matched initialization, plus 21 indexed evidence hashes. Manifest contains file sizes and hashes without compound-level outcomes.
