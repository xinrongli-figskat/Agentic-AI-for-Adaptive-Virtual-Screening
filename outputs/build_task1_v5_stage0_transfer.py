"""Build a small, hash-manifested transfer for the Task 1 v4 closeout."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import zipfile


HERE = Path(__file__).resolve().parent
FILES = {
    "closeout_task1_v4.py": "closeout_task1_v4.py",
    "test_closeout_task1_v4.py": "test_closeout_task1_v4.py",
    "verify_task1_v4_archive.py": "verify_task1_v4_archive.py",
    "docs/task1_v5/task1_v5_source_adjudication_rules_20261016.md": "task1_v5_source_adjudication_rules_20261016.md",
    "docs/task1_v5/task1_v5_execution_plan_20261016.md": "task1_v5_execution_plan_20261016.md",
    "docs/task1_v5/task1_v5_protocol_lock_20261016.json": "task1_v5_protocol_lock_20261016.json",
}


def main():
    manifest = {"format": "task1_v5_stage0_transfer_v1", "files": {}}
    for target, source in FILES.items():
        payload = (HERE / source).read_bytes()
        manifest["files"][target] = hashlib.sha256(payload).hexdigest()
    dest = HERE / "task1_v5_stage0_transfer.zip"
    if dest.exists():
        dest.unlink()
    with zipfile.ZipFile(dest, "x", compression=zipfile.ZIP_DEFLATED) as bundle:
        for target, source in FILES.items():
            bundle.write(HERE / source, target)
        bundle.writestr("TRANSFER_MANIFEST.json", json.dumps(manifest, indent=2) + "\n")
    with zipfile.ZipFile(dest) as bundle:
        assert set(bundle.namelist()) == set(FILES) | {"TRANSFER_MANIFEST.json"}
        for name, wanted in manifest["files"].items():
            assert hashlib.sha256(bundle.read(name)).hexdigest() == wanted
    sha = hashlib.sha256(dest.read_bytes()).hexdigest()
    (HERE / "task1_v5_stage0_transfer.sha256").write_text(sha + "  " + dest.name + "\n", encoding="ascii")
    print(json.dumps({"archive": str(dest), "sha256": sha, "bytes": dest.stat().st_size,
                      "files": len(FILES)}, indent=2))


if __name__ == "__main__":
    main()
