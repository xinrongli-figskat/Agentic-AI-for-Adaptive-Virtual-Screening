# D8 run log

Started: 2026-10-22 (local desktop session; post-exposure).
Finalized UTC: 2026-10-22T08:18:51.650601+00:00

- Reconciled D7-A/B/C2/C3/D/E, C4, and publication stop from local receipts. No Git command or Git state change was made.
- Reviewed and wrote the English advisor summary, glossary, and measurement-effort note. Automated scan found no listed internal terminology in the two advisor-facing documents.
- Locked the library-visible controller and public inputs before synthetic tests. Three unit tests passed. Full TNAP public candidate set preflight passed (462/462 keys and structures; no unqueried outcomes; hidden-outcome perturbation invariant).
- One synthetic-only glm-5.3-flash API probe succeeded with do_sample=false. Provider usage: 47,598 prompt tokens, 85 completion tokens, 47,683 total. No campaign oracle call.
- Re-evaluated 62 numerically passing rows using the saved R3 metrics and D7-D identity audit. One existing source-limited set remains usable; two rows are only candidates for limited source review; 59 remain unadmitted on identity evidence. No new pool or labels created.
- Completed decoy, BindingDB-ranking, and prediction-method scope notes.
- Deferred the optional 40-request library-visible checkpoint. The full-library probe already consumed 47,598 provider prompt tokens; the optional experiment would be a separate performance evaluation, not an interface validation.
- D8 Task 2 request ledger: baseline 521 + completed C4 161 + synthetic API probe 1 = 683 physical requests. D8 itself added one provider request.
