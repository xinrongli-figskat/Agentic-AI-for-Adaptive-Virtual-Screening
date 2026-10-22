"""Read-only verification of D10 and cited evidence, then write D10 manifest."""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
PRIVATE = HERE / "d10_private/runs"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    result = json.loads((HERE / "D10_D9_MATCHED_MIX.json").read_text(encoding="utf-8"))
    lock = json.loads((HERE / "D10_LOCK.json").read_text(encoding="utf-8"))
    for key, path in (("protocol", HERE / "D10_PROTOCOL.md"),
                      ("runner", HERE / "run_d10.py"),
                      ("D9_analysis", ROOT / "outputs/d9_20261022/D9_ANALYSIS.json")):
        assert digest(path) == lock["sha256"][key], f"Lock mismatch: {key}"
    assert result["lock_sha256"] == digest(HERE / "D10_LOCK.json")
    assert result["deterministic_full_trajectory_replay"] is True
    assert result["same_seed_initialization_verified_against_D9"] is True
    assert result["GLM_calls"] == 0
    assert result["source_behavior_weights"] == {"greedy_like": 54, "diverse_like": 17, "random": 9}
    assert result["mean_mixture_H50"] == 12.85
    assert result["mean_D9_minus_mixture"] == 1.4
    assert result["paired_bootstrap_95_interval"] == [-0.4, 3.25]
    assert len(result["mixture_H50_by_seed"]) == 20
    assert sum(result["mixture_H50_by_seed"]) == 257
    assert sum(result["D9_H50_by_seed"]) == 285
    assert len(list(PRIVATE.glob("seed*.json"))) == 20
    for seed in range(20):
        run = json.loads((PRIVATE / f"seed{seed}.json").read_text(encoding="utf-8"))
        assert run["seed"] == seed and run["H50"] == result["mixture_H50_by_seed"][seed]
        trajectory = run["trajectory"]
        assert len(trajectory) == 5
        keys = [key for stage in trajectory for key in stage["selection"]]
        assert len(keys) == len(set(keys)) == 50
        d9 = json.loads((ROOT / f"outputs/d9_20261022/d9_private/runs/seed{seed}/run.json").read_text(encoding="utf-8"))
        assert trajectory[0]["selection"] == d9["trajectory"][0]["selection"]

    index = (HERE / "MANUSCRIPT_EVIDENCE_INDEX.md").read_text(encoding="utf-8")
    pattern = r"`(outputs/[^`]+?)`\s+—\s+`([0-9a-f]{64})`"
    matches = re.findall(pattern, index)
    assert len(matches) >= 15, "Too few indexed file hashes"
    for relative, expected in matches:
        path = (ROOT / relative).resolve()
        assert path.is_relative_to(ROOT), f"Unsafe evidence path: {relative}"
        assert path.exists(), f"Missing indexed evidence: {relative}"
        assert digest(path) == expected, f"Evidence hash mismatch: {relative}"

    inventory = []
    for path in sorted(HERE.rglob("*")):
        if path.is_file() and path.name != "MANIFEST.json":
            inventory.append({"path": path.relative_to(HERE).as_posix(),
                              "bytes": path.stat().st_size, "sha256": digest(path),
                              "private_trajectory": path.is_relative_to(PRIVATE)})
    manifest = {
        "schema": "d10_closeout_manifest_v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "status": "complete_post_exposure_cpu_only",
        "GLM_calls_D10": 0,
        "project_cumulative_physical_api_requests_unchanged": 764,
        "git_operations_D10": 0,
        "D3_to_D9_files_modified": 0,
        "indexed_evidence_hashes_verified": len(matches),
        "D10_files": inventory,
    }
    (HERE / "MANIFEST.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": manifest["status"], "files": len(inventory),
                      "evidence_hashes_verified": len(matches), "private_runs": 20}, ensure_ascii=False))


if __name__ == "__main__":
    main()
