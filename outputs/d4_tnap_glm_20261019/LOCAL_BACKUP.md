# D4 local/remote evidence locations

The authoritative completed D4 run is on `lab-4090` at `/driveA/xinrong/agentic-screening/outputs/d4_tnap_glm_20261019/` (117 files in its final manifest). Its final `MANIFEST.json` SHA-256 is `1eb690658a062d959aa52750d849529a0a557bcdb1371ac86a41b7de3bb3af37`.

A complete byte-for-byte mirror is in the adjacent Git-ignored directory `remote_backup_private_20261019/d4_tnap_glm_20261019/`, including per-compound trajectories, private analyses, all preflight artifacts, the first failed analysis attempt and the repaired attempt. Run `python -B outputs/d4_tnap_glm_20261019/verify_d4_backup.py` from the project root to recheck all 117 originally manifested files. This verification passed on 2026-10-19. A later cost-ledger addendum and its separate hash lock are mirrored there as well; the original 117-file manifest was deliberately left unchanged.

The Git-visible root of this directory holds the D4 specification, budget and power lock, code, preflight receipts, summary tables and reports. Do not move or add files from the private mirror into Git: the 40 GLM and 42 matched trajectories contain revealed labels and selected compound IDs. The local root is a curated view and is not meant to match the remote root manifest on its own.

Final status: `done`; Tier A mechanical repair 1/2; Tier B 0; Tier C 0. The earlier D3 freeze and D1/D2 outputs were not rewritten.
