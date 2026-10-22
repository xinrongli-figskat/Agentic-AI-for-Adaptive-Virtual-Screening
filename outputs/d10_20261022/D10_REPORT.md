# D10 closeout report — 2026-10-22

**Status:** complete. This post-exposure work added one CPU control and documentation. It made **zero GLM calls**; the recorded project cumulative physical API-request count remains **764**. It did not use Git, freeze a new evaluation set, alter labels or thresholds, or modify D3–D9 historical outputs.

## D9-frequency-matched CPU control

The analysis rule and its interpretation were saved in `D10_PROTOCOL.md` and locked at **2026-10-22T14:45:43.704009+00:00**, before the CPU result file was written at **2026-10-22T14:46:33.940635+00:00**. The lock SHA-256 is `72dd56c221287d0b08be42597063fa82541df8fe9c626c856768c189e24b91f8`. It pins the protocol, runner and D9 analysis hashes. The existing D9 analysis was checked for its 20-seed outcome vector, mean **14.25**, and actual behavior counts **54 greedy / 17 diverse / 9 random** before this control ran.

The control used the same frozen TNAP set and `S_strong` predictions, bit representation, 20 seed-specific initial sets, 50-query budget, and three underlying selection behaviors as D9. SHA-256 draws used the prespecified 54/17/9 weights. The complete 20-seed calculation was repeated from the same inputs; **all full trajectories matched exactly**, including the initial selections and revealed results. Every run made 50 distinct selections. Two replays took **39.12 CPU seconds** in total. The 20 first-replay trajectories are in `d10_private/runs/`; they contain measured outcomes and should remain private.

| Quantity | Result |
|---|---:|
| Draw weights (greedy / diverse / random) | 54 / 17 / 9 out of 80 |
| Actual SHA-256 draws | 46 / 24 / 10 |
| Executed behavior, after one-class random fallback | 39 / 24 / 17 |
| CPU mixture mean active compounds within 50 selections | **12.85** |
| D9 library-visible controller mean | **14.25** |
| Same-seed D9 minus mixture mean | **+1.40** |
| Paired seed-bootstrap 95% interval, 10,000 resamples, seed 20261018 | **−0.40 to +3.25** |

The interval includes zero, selecting the **prewritten “no detectable timing contribution beyond rule-frequency preference” branch**. The data remain compatible with a positive timing effect as large as the interval's upper end. This is one SHA-256 mixture realisation; the seed bootstrap does not include uncertainty over alternative mixture draw streams. Moreover, the finite draw and fallback caused the CPU comparator to execute fewer greedy and more random batches than D9 itself (39/24/17 versus 54/17/9). The comparison therefore matches **sampling weights**, not exact realised counts. It does not isolate a causal timing effect as cleanly as an exact-count control would. We did not change weights or rerun with a different stream after seeing the result.

The task card's **+0.29** arithmetic forecast was not used in the analysis. The observed difference is **+1.40**, which is **1.11** higher. This discrepancy is reported, not tuned away. The positive point estimate does not override the paired interval's inclusion of zero.

## Closing interpretation and writing material

`SUMMARY_FOR_ADVISOR_v3.md` keeps the external account in conventional scientific language and updates the prior summary with this control. It states three bounded observations: the tested benefit is consistent with an improved overall rule preference while no distinct timing benefit is detected; showing the preset library improves the controller over its summary-only version in this one cell; a retrospectively selected fixed greedy rule still performs better. It explicitly notes the predictor, menu and prompt differences that prevent direct comparison with earlier experiments, and the fact that this study does not answer how benefit changes with prediction-method accuracy.

`MANUSCRIPT_EVIDENCE_INDEX.md` maps candidate manuscript numbers to their local evidence files, current SHA-256 values and timing status. It distinguishes locks made before the respective runs from post-exposure descriptive analyses. These hashes support traceability, not external validation or rights to publish private trajectory files.
