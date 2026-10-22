"""Seal D5 public evidence without including label-bearing private trajectories."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def main():
    base = Path(__file__).resolve().parent
    paths = [p for p in base.iterdir() if p.is_file() and p.name != "MANIFEST.json"]
    paths += list((base / "e_menu").glob("*.py"))
    paths += [base / part / "MANIFEST.json"
              for part in ("a_mechanism", "b_report_fix", "c_zeroshot", "d_task1_auto")]
    assert all(p.is_file() for p in paths)
    assert all("private" not in p.parts for p in paths)
    files = []
    for path in sorted(paths, key=lambda p: str(p.relative_to(base))):
        files.append({"path": str(path.relative_to(base)).replace("\\", "/"),
                      "bytes": path.stat().st_size,
                      "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    manifest = {"utc": datetime.now(timezone.utc).isoformat(),
                "status": "done", "scope": "D5 public summary and code; private trajectories backed up separately",
                "file_count": len(files), "files": files}
    target = base / "MANIFEST.json"
    target.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"file_count": len(files),
                      "manifest_sha256": hashlib.sha256(target.read_bytes()).hexdigest()}))


if __name__ == "__main__":
    main()
