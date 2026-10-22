# D7-D S-1 revision v3 execution log

Post-exposure. This revision performs CPU-only credential recalculation from hash-locked, raw global and assay-provenance facts captured in the first wave. It makes zero GLM calls. It creates no campaign-ready pool and changes none of the parent directory's existing files.

The source addendum SHA-256 was verified as fb5b81850f20aa7353ca564a6615f78f85f8694a05dad71af1189e5e7f36ced8. It authorizes the six S-1 decisions. The root had verified the frozen database and other D7 prerequisites. This revision independently verifies every member of the 24-file parent manifest before and after recalculation; the raw-facts input hash is recorded in input_verification.json.

- Rule lock: 2026-10-21T11:22:43.074712+00:00. Exact authorized S-1 text and operational rule hashes are in rule_v3_lock.json.
- Measurement start: 2026-10-21T11:24:08.619304+00:00; completed 11:24:09.353040+00:00. These are generated receipt timestamps, not inferred file modification times.
- Results: 62 rows, 25,813 support identities, four fractions sum to one in every row, five multi-molregno occurrences all de minimis. All unresolvable fractions are zero.
- Source funnel: 43/62 candidates have assay support from src_id 37; 56/62 are T2 patent, three T1, three T3.
- Credentials: three T1 pass, 56 patent and three literature fail G2. No G1 block. TACE is blocked by G2 (not G1); TNAP passes T1. These satisfy the predeclared checks but do not independently validate the calibrated rule.
- Eight unseen candidates locked at 2026-10-21T11:24:09.356040+00:00, selected by original R3 rank excluding six exposed references, without filtering by credential results.
- Independent verification at 2026-10-21T11:25:34.022748+00:00: eight gate boundary/conjunction cases pass; all 62 credential/gate rows recompute; old manifest members unchanged; all campaign_ready fields false.

Direction statements and scientific interpretation limits are in DEVIATION_S1_RULE_V3.md. Public aggregates contain no per-compound hidden results. Per-identity provenance is stored only in Git-ignored identity_private/. The source-review-complete fields describe this credential computation, which did not perform a new source review; they do not replace historical TNAP or other candidate decisions.

Await root release before any A-4 GLM calls. Planned 8 × 4 decisions, maximum 40 total attempts, remain unused.
