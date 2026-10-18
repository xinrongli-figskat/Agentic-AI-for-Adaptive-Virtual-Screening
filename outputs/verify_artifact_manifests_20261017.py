"""Read-only verification of new private task artifacts."""

import hashlib
import json
import sys
from pathlib import Path


def verify(root):
    root = Path(root).resolve()
    manifest_path = root / "MANIFEST.json"
    raw = manifest_path.read_bytes()
    manifest = json.loads(raw)
    if manifest.get("status") != "done" or (root / "STATUS").read_text().strip() != "done":
        raise ValueError(f"Not done: {root}")
    seen = set()
    for item in manifest["files"]:
        path = (root / item["path"]).resolve()
        if not path.is_relative_to(root) or path == manifest_path or path in seen:
            raise ValueError(f"Unsafe/duplicate path: {item['path']}")
        seen.add(path)
        if path.stat().st_size != item["bytes"]:
            raise ValueError(f"Size mismatch: {path}")
        h = hashlib.sha256()
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                h.update(block)
        if h.hexdigest() != item["sha256"]:
            raise ValueError(f"Hash mismatch: {path}")
    return {"root": str(root), "files_verified": len(seen),
            "manifest_sha256": hashlib.sha256(raw).hexdigest()}


if __name__ == "__main__":
    for name in sys.argv[1:]:
        print(json.dumps(verify(name), ensure_ascii=False))
