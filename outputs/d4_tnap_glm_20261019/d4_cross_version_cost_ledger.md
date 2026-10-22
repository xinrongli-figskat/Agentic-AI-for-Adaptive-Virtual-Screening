# D4 cross-version returned-token ledger

This is a **scope-limited research ledger**, not a Zhipu invoice. It adds non-overlapping reported scopes once; provider-side charges and usage absent from failed calls cannot be inferred.

| Scope | Recorded work | Prompt tokens returned | Completion tokens returned | Total returned |
|---|---:|---:|---:|---:|
| Task 1 v1–v4 cumulative through attempt 72 | 72 GLM attempts in the final v4 status (includes inherited v1–v3, so those are not added again) | 313,417 | 17,572 | 330,989 |
| DYRK3 completed GLM campaigns, old seeds 0–4 | 40 completed decisions | 97,956 | 2,551 | 100,507 |
| DYRK3 D2-2 new seeds 5–19 | 120 completed decisions | 285,146 | 6,781 | 291,927 |
| TNAP D4 campaigns | 160 completed decisions, 160 HTTP attempts | 382,177 | 8,743 | 390,920 |
| TNAP D4 synthetic-only preflight probe | 1 successful HTTP attempt | 433 | 44 | 477 |
| **Audited subtotal of these scopes** | Different kinds of attempts/decisions; do not sum as a common request count | **1,079,129** | **35,691** | **1,114,820** |

The Task 1 row comes from the final v4 status shown by the operator, and the DYRK3 rows from `outputs/d2_controls_20261019/attempt2_20261019/d2_summary.md`; D4 rows come from the locked synthetic probe and `post_glm_verification.json`. D4's 1,109 reasoning tokens are a **subset** of its 8,743 completion tokens, not an extra charge or token count. The subtotal excludes other historical probes, unreturned usage from earlier DYRK3 failures, and any model/provider charges not represented by these returned usage fields. D3 and the D4 matched-policy CPU arm made zero GLM requests. Model service time, CPU feature/analysis/selection time, and upstream data-acquisition time are separately reported in `d4_report.md`.
