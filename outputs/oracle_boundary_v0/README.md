# Synthetic oracle boundary dry run v0

This small package checks the next safety boundary without running an LLM or querying real outcomes. The pre-freeze candidate export is verified read-only; the budgeted oracle is tested with **synthetic** labels on 231 artificial candidates. It checks the full 10-initialization + four 10-query-batch schedule, invalid and repeated IDs, pool integrity and hidden-label exposure through `public_state`.

After copying this folder to the remote Ubuntu project:

```bash
cd /driveA/xinrong/agentic-screening
source .venv/bin/activate
python oracle_boundary_v0/test_oracle_boundary.py
python oracle_boundary_v0/verify_prepared.py \
  --public-dir /driveA/xinrong/agentic-screening/data/campaign_public/prefreeze_20261014T145140Z_6402306a507c6fd5 \
  --private-dir /driveA/xinrong/agentic-screening/data/curation_private/prefreeze_20261014T145140Z_6402306a507c6fd5
```

Expected: two synthetic tests pass, and the read-only verification prints `verified: true`, `candidate_count: 231`, `pool_id: 6402306a507c6fd5` and the public candidate SHA-256. It prints **no labels**. The verification uses the private file only to check its recorded checksum and matching IDs; the test oracle uses synthetic labels, never the real DYRK3 labels.

The current receipt remains `pre_freeze_export_not_campaign_ready`. This is intentionally not a real campaign. The later LLM wrapper must expose only the allowed public state, numerical tools and `query_batch_tool` to the model. It must not expose arbitrary shell, file browsing or public bioactivity lookup. A fixed controller, numerical scoring tools, full protocol, monitoring/logs and GLM configuration remain to be implemented and hashed before real evaluation.
