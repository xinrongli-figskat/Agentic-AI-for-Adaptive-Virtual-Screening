"""Read-only verifier for the four independently sealed D5 wave-one outputs."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


BASE = Path(__file__).resolve().parent
NAMES = ("a_mechanism", "b_report_fix", "c_zeroshot", "d_task1_auto")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    results = {}
    for name in NAMES:
        folder = BASE / name
        manifest_path = folder / "MANIFEST.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        listed = manifest["files"]
        if isinstance(listed, dict):
            listed = [dict(path=key, **value) for key, value in listed.items()]
        assert isinstance(listed, list) and listed, name
        paths = set()
        for row in listed:
            relative = Path(row["path"])
            assert not relative.is_absolute() and ".." not in relative.parts, row
            path = (folder / relative).resolve(strict=True)
            assert path.is_relative_to(folder.resolve()) and path.is_file(), row
            assert sha256(path) == row["sha256"], path
            assert path.stat().st_size == row["bytes"], path
            assert relative.as_posix() not in paths, row
            paths.add(relative.as_posix())
        actual = {path.relative_to(folder).as_posix() for path in folder.rglob("*")
                  if path.is_file() and path.name != "MANIFEST.json"
                  and "__pycache__" not in path.parts and path.suffix != ".pyc"}
        assert actual == paths, {"directory": name,
                                 "unlisted": sorted(actual - paths),
                                 "missing": sorted(paths - actual)}
        assert (folder / "STATUS").exists(), name
        results[name] = {"manifest_sha256": sha256(manifest_path),
                         "file_count": len(paths), "status": (folder / "STATUS").read_text().strip(),
                         "glm_calls": manifest.get("glm_calls")}
    task1_metrics = json.loads((BASE / "d_task1_auto" / "metrics.json").read_text(encoding="utf-8"))
    assert task1_metrics["api_attempts"] == 24 <= task1_metrics["allowed_max_api_attempts"] == 30
    assert task1_metrics["completed_candidate_n"] == 6
    assert task1_metrics["candidate_assays_outside_scope_called"] == []
    results["d_task1_auto"]["glm_calls"] = task1_metrics["api_attempts"]
    root_files = {p.name for p in BASE.iterdir() if p.is_file()}
    allowed_root_files = {"d5_task_card_source.md", "d5_user_amendments.md", "d5_baseline.json",
                          "verify_wave1.py", "wave1_verification.json"}
    assert root_files <= allowed_root_files, sorted(root_files - allowed_root_files)
    report = {"verified_at_utc": datetime.now(timezone.utc).isoformat(),
              "all_member_hashes_pass": True,
              "directories_checked": list(NAMES),
              "cross_writes_in_d5_tree_observed": False,
              "note": "All agent manifests refer only to their own directory and the D5 root has only main-agent files; this does not audit every path outside the D5 tree. Frozen source hashes are checked separately.",
              "results": results}
    output = BASE / "wave1_verification.json"
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
