"""Seal the B-only output directory with hashes and source provenance."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from calculate_strategy_gradient import ANALYSIS, D4, RUNS, HERE, compute


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    results, run_hashes = compute()
    assert len(run_hashes) == 40
    assert (HERE / "STATUS").read_text(encoding="utf-8").strip() == "done"
    files = {}
    for path in sorted(HERE.iterdir()):
        if path.is_file() and path.name != "MANIFEST.json":
            files[path.name] = {"sha256": sha(path), "bytes": path.stat().st_size}
    canonical_hashes = json.dumps(run_hashes, sort_keys=True, separators=(",", ":")).encode()
    manifest = {
        "schema": "d5_b_report_fix_manifest_v1",
        "status": "done",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "post_exposure": True,
        "glm_calls": 0,
        "source": {
            "d4_analysis_sha256": sha(ANALYSIS),
            "d4_post_glm_verification_sha256": sha(D4 / "post_glm_verification.json"),
            "run_count": len(run_hashes),
            "sorted_run_hashes_json_sha256": hashlib.sha256(canonical_hashes).hexdigest(),
        },
        "analysis": {
            "decision_count_per_representation": {rep: sum(sum(c.values()) for c in value["counts"].values())
                                                  for rep, value in results.items()},
            "multiple_comparisons_adjusted": False,
        },
        "files": files,
    }
    (HERE / "MANIFEST.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"manifest_sha256": sha(HERE / "MANIFEST.json"), "files": len(files)}, indent=2))


if __name__ == "__main__":
    main()
