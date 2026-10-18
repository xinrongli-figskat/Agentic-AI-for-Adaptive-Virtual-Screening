"""Restore the frozen ChEMBL download prefix after stopping a competing writer."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys


def main() -> None:
    root = Path(sys.argv[1]).resolve(strict=True)
    manifest = json.loads((root / "segments_manifest.json").read_text())
    prefix = root / "prefix.part"
    length = manifest["prefix_bytes"]
    if prefix.stat().st_size < length:
        raise ValueError("Prefix shorter than frozen manifest")
    digest = hashlib.sha256()
    with prefix.open("rb") as stream:
        remaining = length
        while remaining:
            block = stream.read(min(16 * 1024 * 1024, remaining))
            if not block:
                raise ValueError("Unexpected end of prefix")
            digest.update(block)
            remaining -= len(block)
    actual = digest.hexdigest()
    prior = manifest["prefix_sha256"]
    if actual != prior:
        # The old curl writer was still appending while the first manifest
        # hashed to EOF. Preserve that manifest and record the correction.
        backup = root / "segments_manifest_pre_repair.json"
        if backup.exists():
            raise FileExistsError("Prior repair manifest already exists")
        backup.write_bytes((root / "segments_manifest.json").read_bytes())
        manifest["prefix_sha256"] = actual
        manifest["prefix_repair_reason"] = "concurrent_old_writer_appended_during_initial_manifest_hash"
        manifest["prefix_sha256_before_repair"] = prior
        (root / "segments_manifest.json").write_text(
            json.dumps(manifest, sort_keys=True, indent=2) + "\n")
    old_size = prefix.stat().st_size
    if old_size > length:
        with prefix.open("r+b") as stream:
            stream.truncate(length)
    print(json.dumps({"status": "frozen_prefix_restored", "old_bytes": old_size,
                      "new_bytes": prefix.stat().st_size,
                      "sha256": actual, "manifest_hash_corrected": actual != prior,
                      "archive_sha256_still_required": True}))


if __name__ == "__main__":
    main()
