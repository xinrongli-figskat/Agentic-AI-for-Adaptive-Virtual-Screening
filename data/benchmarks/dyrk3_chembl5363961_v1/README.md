# DYRK3 feasibility pool: public candidate interface

`public/candidates.jsonl` is the existing 231-compound public export, copied byte-for-byte from the verified 2026-10-15 workstation backup. Each row contains only `compound_key` and `standardized_smiles`.

`public/public_receipt.json` is the original **pre-freeze export receipt**; it must not be mistaken for a separate freeze receipt. `freeze_manifest.json` is the original frozen DYRK3 v1 manifest. Its `data_sha256.public_candidates` matches the published candidate file (`0e1d745fe49c9d5f1aeed732f54388ece05b56f5670c424db92e4c7711943800`). The manifest records hashes and private source paths but no compound outcomes. The private labels and activity values are not distributed.

This pool is a historical feasibility example, not a newly qualified benchmark.
