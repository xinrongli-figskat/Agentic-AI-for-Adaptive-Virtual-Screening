# D6-A execution log

This directory is a post-exposure D6-A record. It contains no GLM request and no candidate decision.

- Start UTC: 2026-10-20T13:24:07Z
- Intended task: A-1 credential measurement for the locked 62-row R3 v2 ranking.
- R3 ranking input: `/driveA/xinrong/agentic-screening/deliveries_20261018/outputs/r3_ranked_numeric_private_20261018_v2/ranked_numeric_qualified_62.csv`
- R3 SHA-256: `dfb3569217454cd73a6c60b69128988aa1f57dc9866b7949728954933add47b9` (matches the D6 card).
- Seven non-database D6 prerequisite hashes were read remotely and matched their D6-card expectations: `campaign_v0/llm_controller.py`, `campaign_v0/campaign_core.py`, the two TNAP freeze files, the DYRK3 manifest, the D5 menu-code lock, and the R3 table.
- ChEMBL database path selected: `/driveA/xinrong/agentic-screening/data/source_dbs/chembl_37/extracted/chembl_37.db`; no database row was modified.
- A read-only inspection of the saved B2 job inputs found 25,808 single-molregno and 5 multi-molregno standardized support identities.
- Tier B stop: the locked A-1 singular-molregno definition does not specify how to credential those five standardized identities. See `BLOCKED_support_identity_mapping.md`.

GLM calls: 0 / 40. Network calls: 0. No threshold, label, pool, campaign code, or historical decision was changed.
