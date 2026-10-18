"""Extract the single SQLite database from a checksum-verified ChEMBL archive."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import tarfile


EXPECTED_ARCHIVE = "33c203740555f96067710cdfc1c3c55d890660e5908ec5cbf5817492c290d281"


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(16 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, required=True)
    args = parser.parse_args()
    root = args.source_dir.resolve(strict=True)
    receipt = json.loads((root / "download_verified.json").read_bytes())
    archive = root / "chembl_37_sqlite.tar.gz"
    if receipt.get("status") != "verified" or receipt.get("archive_sha256") != EXPECTED_ARCHIVE:
        raise ValueError("Official download verification receipt is absent or unexpected")
    if digest(archive) != EXPECTED_ARCHIVE:
        raise ValueError("Archive bytes fail the official SHA-256")
    extracted = root / "extracted"
    extracted.mkdir(exist_ok=True)
    destination = extracted / "chembl_37.db"
    completed = extracted / "extraction_verified.json"
    if completed.exists():
        saved = json.loads(completed.read_bytes())
        if saved.get("database_sha256") != digest(destination):
            raise ValueError("Previously extracted database has changed")
        print(json.dumps({"status": "already_extracted", **saved}), flush=True)
        return
    if destination.exists():
        raise FileExistsError("Database exists without extraction receipt")
    temp = extracted / "chembl_37.db.partial"
    if temp.exists():
        raise FileExistsError("Partial extraction requires inspection")
    member_name = None
    db_hash = hashlib.sha256()
    with tarfile.open(archive, mode="r|gz") as source:
        for member in source:
            if member.issym() or member.islnk():
                raise ValueError("Unexpected link in release archive")
            if not member.isfile():
                continue
            if not member.name.lower().endswith((".db", ".sqlite", ".sqlite3")):
                continue
            if member_name is not None:
                raise ValueError("Multiple SQLite files in release archive")
            member_name = member.name
            with temp.open("xb") as output:
                stream = source.extractfile(member)
                if stream is None:
                    raise ValueError("Could not read SQLite archive member")
                while True:
                    block = stream.read(16 * 1024 * 1024)
                    if not block:
                        break
                    output.write(block)
                    db_hash.update(block)
            if temp.stat().st_size != member.size:
                raise ValueError("Extracted member byte count mismatch")
    if member_name is None:
        raise ValueError("No SQLite member in release archive")
    uri = "file:" + str(temp) + "?mode=ro"
    with sqlite3.connect(uri, uri=True) as connection:
        tables = {row[0].lower() for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not {"activities", "assays", "target_dictionary", "docs", "compound_structures"} <= tables:
            raise ValueError("Extracted SQLite schema is incomplete")
    os.replace(temp, destination)
    report = {"schema": "chembl37_sqlite_extraction_v1", "archive_sha256": EXPECTED_ARCHIVE,
              "archive_member": member_name, "database_sha256": db_hash.hexdigest(),
              "database_bytes": destination.stat().st_size, "status": "verified_extraction"}
    completed.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n")
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()
