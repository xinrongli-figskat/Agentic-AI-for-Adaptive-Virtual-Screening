"""Verify the D5 public manifest without changing it."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


def main():
    base = Path(__file__).resolve().parent
    manifest = json.loads((base / "MANIFEST.json").read_text(encoding="utf-8"))
    assert manifest["file_count"] == len(manifest["files"])
    for item in manifest["files"]:
        path = (base / item["path"]).resolve()
        assert path.is_relative_to(base)
        assert path.is_file() and path.stat().st_size == item["bytes"], item["path"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"], item["path"]
    print(json.dumps({"status": "pass", "file_count": manifest["file_count"],
                      "manifest_sha256": hashlib.sha256((base / "MANIFEST.json").read_bytes()).hexdigest()}))


if __name__ == "__main__":
    main()
