"""Verify the completed private D2-1 output and index public attempt files."""
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PRIVATE = ROOT / "d2_rule_adaptive_private_20261019"
EXPECTED_PRIVATE_MANIFEST = "3cb895e3fe9a18ddfc17d91564cd0103febc90861e13d4f139e03328011b40ac"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_manifest(folder, paths, external=None):
    files = [{"path": p.relative_to(folder).as_posix(), "bytes": p.stat().st_size,
              "sha256": sha(p)} for p in sorted(paths) if p.name != "MANIFEST.json"]
    body = {"files": files, "self_excluded": True}
    if external:
        body["private_manifest_sha256"] = external
    (folder / "MANIFEST.json").write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8")


def main():
    assert (PRIVATE / "STATUS").read_text().strip() == "done"
    assert sha(PRIVATE / "MANIFEST.json") == EXPECTED_PRIVATE_MANIFEST
    manifest = json.loads((PRIVATE / "MANIFEST.json").read_text())
    for row in manifest["files"]:
        target = PRIVATE / row["path"]
        assert target.is_file() and target.stat().st_size == row["bytes"]
        assert sha(target) == row["sha256"], row["path"]
    assert (ROOT / "STATUS").read_text().strip() == "done"
    arms = ROOT / "d2_arms"
    write_manifest(arms, arms.glob("*"))
    write_manifest(ROOT, (p for p in ROOT.iterdir() if p.is_file()),
                   external=EXPECTED_PRIVATE_MANIFEST)
    print(json.dumps({"verified_private_files": len(manifest["files"]),
                      "private_manifest_sha256": EXPECTED_PRIVATE_MANIFEST,
                      "public_manifest_sha256": sha(ROOT / "MANIFEST.json")}))


if __name__ == "__main__":
    main()
