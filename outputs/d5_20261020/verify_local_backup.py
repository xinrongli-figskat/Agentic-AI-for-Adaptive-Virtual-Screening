"""Verify the Git-excluded local copy of the D5 private trajectory archive."""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path


def main():
    project = Path(__file__).resolve().parents[2]
    base = Path(__file__).resolve().parent
    archive = project / ".sync_audit/d5_20261020/d5_e_menu_private_20261020.zip"
    receipt = json.loads((base / "d5_private_backup_receipt.json").read_text())
    expected = json.loads((base / "d5_final_verification.json").read_text())["private_run_file_hashes"]
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    assert digest == receipt["archive_sha256"]
    with zipfile.ZipFile(archive) as bundle:
        assert set(bundle.namelist()) == set(expected)
        assert bundle.testzip() is None
        for name, expected_hash in expected.items():
            assert hashlib.sha256(bundle.read(name)).hexdigest() == expected_hash, name
    print(json.dumps({"status": "pass", "archive_sha256": digest,
                      "private_members_verified": len(expected),
                      "git_excluded_path": str(archive)}))


if __name__ == "__main__":
    main()
