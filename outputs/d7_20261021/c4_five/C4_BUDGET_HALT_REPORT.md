# C4 physical-call ceiling checkpoint — 2026-10-21

This is an additive post-exposure checkpoint, not the planned C4 result. The [locked protocol](C4_PROTOCOL_v1.md) caps this authorization at **160 physical GLM calls**. The runner reached that ceiling and stopped before the last decision in TNAP × `S_strong` × bit. No extra call was made.

The [offline audit](C4_BUDGET_HALT_AUDIT.json), SHA-256 `7fde1ee182d8749b0f6c2e5ed515687d08082c7a7dc8024ea7408c31db0e48db`, verified:

- 39 of 40 planned campaigns are complete. Repeat 2, seed 19 has 40 distinct queries and three completed feedback batches; its fourth decision and last 10 queries are pending.
- The 160 physical attempts comprise 158 successful model responses and two transport failures. All 158 saved model responses passed the strict decision schema; there were zero format failures. One batch was an automatic continuation of an earlier persistent-random choice, so 159 feedback batches have been executed.
- The saved 1,990 oracle queries match the frozen private labels, with no repeated compound within a campaign and no ENS or out-of-menu choice. Returned usage for successful responses is 89,399 prompt tokens and 11,914 completion tokens (101,313 total). The two failed transport attempts have no returned token usage, and these token counts are not a monetary bill.
- The private tree digest is `bd0c9301939dd30b4916a62d03db7f4625c39e546db0ae427225b8980e6138ad`. Real responses, trajectories, and labels remain under `outputs/d7_20261021/c4_five_private`, which is Git-ignored; the public report contains no individual labels or raw provider responses.

The preregistered primary comparison is **not complete**. Neither an imputed last batch nor an unbalanced 39-campaign estimate will be presented as its result. One further successful strict-format decision would finish the matrix. The existing authorization does not allow it. An extension, if approved, should be limited to this one pending decision; a ceiling of four additional physical attempts would accommodate a transport interruption and the already specified one-time identical-prompt format correction. The runner and original locked files must remain unchanged; any extension is an additive, dated authorization and deviation record.
