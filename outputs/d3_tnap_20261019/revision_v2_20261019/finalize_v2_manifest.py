"""Finalize a self-excluded manifest for the blocked D3-1 v2 revision."""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for part in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            h.update(part)
    return h.hexdigest()


def main():
    if (ROOT / "STATUS").read_text().strip() != "blocked":
        raise ValueError("D3-1 v2 status must be blocked")
    files = [{"path": p.relative_to(ROOT).as_posix(), "bytes": p.stat().st_size,
              "sha256": sha(p), "private": "_private_" in p.as_posix()}
             for p in sorted(ROOT.rglob("*")) if p.is_file() and p.name != "MANIFEST.json"]
    data = {"schema": "d3_tnap_homogeneity_v2_blocked_manifest_v1",
            "created_utc": datetime.now(timezone.utc).isoformat(), "status": "blocked",
            "blocker": "h3_validator_ordinal_coverage", "glm_calls": 0,
            "h1_passed": True, "h2_passed": True, "h3_passed": False,
            "rule_sha256": "64578594c0f3e25745a31110cb0d95799a98cd0cebbac7f37d83f1b85794d5c7",
            "first_failure_assertion_sha256": "b4bb2d52646dc682362cadc28540716b8199855d955051fffd9d23056afa9ad8",
            "original_reconciliation_sha256": "b22d9ca229c8b264c19e3dba8a4b38af5b1246438e7382fc989df7d284c12e5f",
            "self_excluded": True, "files": files}
    (ROOT / "MANIFEST.json").write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    print(sha(ROOT / "MANIFEST.json"))


if __name__ == "__main__":
    main()
