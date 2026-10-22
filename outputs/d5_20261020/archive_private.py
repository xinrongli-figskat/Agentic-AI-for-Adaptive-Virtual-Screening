"""Seal D5 private campaign trajectories into a local-only backup."""

from __future__ import annotations

import json
import os
import zipfile
from pathlib import Path

from outputs.d5_20261020.e_menu.run_extended import BASE, PRIVATE_OUT, ROOT, sha, utc


def main():
    verified = json.loads((BASE / "d5_final_verification.json").read_text())
    expected = verified["private_run_file_hashes"]
    assert len(expected) == 760
    archive_dir = ROOT / "data/curation_private/d5_backups"
    archive_dir.mkdir(parents=True, exist_ok=True)
    archive_path = archive_dir / "d5_e_menu_private_20261020.zip"
    temp = archive_path.with_suffix(".zip.tmp")
    if archive_path.exists() or temp.exists():
        raise FileExistsError("D5 private backup already exists; no overwrite")
    with zipfile.ZipFile(temp, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as bundle:
        for relative, digest in sorted(expected.items()):
            path = ROOT / relative
            assert path.is_relative_to(PRIVATE_OUT)
            assert sha(path) == digest
            bundle.write(path, arcname=relative)
    with zipfile.ZipFile(temp) as bundle:
        assert set(bundle.namelist()) == set(expected)
        assert bundle.testzip() is None
    os.chmod(temp, 0o600)
    temp.replace(archive_path)
    receipt = {"utc": utc(), "status": "pass", "archive": str(archive_path),
               "archive_sha256": sha(archive_path), "archive_bytes": archive_path.stat().st_size,
               "member_count": len(expected),
               "source_verification_sha256": sha(BASE / "d5_final_verification.json"),
               "contains_private_labels": True, "git_excluded": True}
    path = BASE / "d5_private_backup_receipt.json"
    path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt))


if __name__ == "__main__":
    main()
