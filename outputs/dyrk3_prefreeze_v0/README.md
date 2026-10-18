# DYRK3 pre-freeze export v0

This package makes **separate public candidate and private label exports** from the previously completed, hash-verified single-assay audit. It does not run a campaign and does not claim the protocol is frozen. The qualification decision and draft protocol are included as snapshots. No network, GLM, or GPU is used.

Run from the Ubuntu project after copying this folder there:

```bash
cd /driveA/xinrong/agentic-screening
source .venv/bin/activate
python dyrk3_prefreeze_v0/test_prepare_pool.py
python dyrk3_prefreeze_v0/prepare_pool.py \
  --audit-run /driveA/xinrong/agentic-screening/data/curation_review/assay_audit_20261014T140422Z_e4a0108b \
  --qualification /driveA/xinrong/agentic-screening/dyrk3_prefreeze_v0/qualification_decision.md \
  --protocol /driveA/xinrong/agentic-screening/dyrk3_prefreeze_v0/protocol_pre_freeze.md \
  --public-root /driveA/xinrong/agentic-screening/data/campaign_public \
  --private-root /driveA/xinrong/agentic-screening/data/curation_private
```

The tool verifies every saved audit hash, source version, target/assay, threshold, one flagged unknown, exact 231-compound/116-hit/115-nonhit counts, IDs, structures, and per-record support. It prints output directories and SHA-256 checksums. The public directory contains only `compound_key` and standardized SMILES plus a public receipt; it does not include outcome values, activity IDs, potency, source paths or private label hashes. The private directory contains the labels, the excluded unknown, source/protocol receipts and decision snapshots. On Linux its directory is mode `0700` and files mode `0600`.

**Separation warning:** Linux permissions protect the private directory from other user accounts. A future campaign process running as the same `xinrong` account could still read it if granted arbitrary shell or file access. The campaign LLM must therefore receive only specifically allowed tools and the public candidate list; its oracle process alone reads the private labels. Public bioactivity lookup is also disallowed during campaigns. The synthetic test checks export integrity and separation, but a later oracle dry run must test the full tool boundary.

The output receipt says `pre_freeze_export_not_campaign_ready` by design. Finalizing the controller/tool configuration, near-threshold sensitivity rule, full protocol hash, and synthetic-oracle dry run remains necessary before a true frozen run.
