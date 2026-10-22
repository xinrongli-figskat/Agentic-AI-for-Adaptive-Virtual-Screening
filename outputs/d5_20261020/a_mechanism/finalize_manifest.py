"""Build a self-excluding D5-A evidence manifest inside this directory only."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]


def sha(path: Path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


assert (OUT / "STATUS").read_text().strip() == "done"
source_paths = {
    "d4_original_manifest_mirror": ROOT / "outputs/d4_tnap_glm_20261019/remote_backup_private_20261019/d4_tnap_glm_20261019/MANIFEST.json",
    "d4_post_glm_verification": ROOT / "outputs/d4_tnap_glm_20261019/post_glm_verification.json",
    "d3_tnap_public_candidates": ROOT / "outputs/d3_tnap_20261019/freeze_tnap_v1/public/candidates.jsonl",
    "d3_tnap_private_labels": ROOT / "outputs/d3_tnap_20261019/freeze_tnap_v1_private_labels/oracle_labels.jsonl",
    "d3_tnap_aggregate": ROOT / "outputs/d3_tnap_20261019/d3_6_report/aggregate.json",
    "frozen_v1_numerical_tools_local_copy": ROOT / "outputs/campaign_v0/numerical_tools.py",
}
files = []
for path in sorted(OUT.rglob("*")):
    if not path.is_file() or path.name == "MANIFEST.json":
        continue
    relative = path.relative_to(OUT).as_posix()
    files.append({"path": relative, "bytes": path.stat().st_size,
                  "sha256": sha(path), "private": "selection_private" in path.parts})
manifest = {
    "schema": "d5_a_mechanism_manifest_v1",
    "created_utc": datetime.now(timezone.utc).isoformat(),
    "status": "done", "glm_calls": 0, "tier_a_repairs": 0,
    "tier_b_or_c_changes": 0,
    "self_excluded": True,
    "read_only_source_sha256": {name: sha(path) for name, path in source_paths.items()},
    "files": files,
}
(OUT / "MANIFEST.json").write_text(
    json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
assert all(sha(OUT / row["path"]) == row["sha256"] for row in files)
print(json.dumps({"manifest_sha256": sha(OUT / "MANIFEST.json"),
                  "files": len(files), "private_files": sum(x["private"] for x in files)}, indent=2))
