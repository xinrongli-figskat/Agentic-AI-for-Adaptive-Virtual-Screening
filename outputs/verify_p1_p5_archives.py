"""Verify a full remote P1/P5 tar.gz copy against its internal file manifest."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import tarfile


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--archive", type=Path, required=True)
    p.add_argument("--expected-sha256", required=True)
    a = p.parse_args()
    archive = a.archive.resolve()
    h = hashlib.sha256()
    with archive.open("rb") as f:
        for block in iter(lambda: f.read(4 * 1024 * 1024), b""):
            h.update(block)
    assert h.hexdigest() == a.expected_sha256
    with tarfile.open(archive, "r:gz") as tar:
        members = [m for m in tar.getmembers() if m.isfile()]
        assert members
        top = PurePosixPath(members[0].name).parts[0]
        assert all(PurePosixPath(m.name).parts[0] == top for m in members)
        assert all(not any(part in ("..", "") for part in PurePosixPath(m.name).parts) for m in members)
        manifest_name = top + "/MANIFEST.json"
        manifest_member = next(m for m in members if m.name == manifest_name)
        manifest_bytes = tar.extractfile(manifest_member).read()
        manifest = json.loads(manifest_bytes)
        listed = {e["path"]: e for e in manifest["files"]}
        assert len(listed) == len(manifest["files"])
        observed = set()
        for m in members:
            if m.name == manifest_name:
                continue
            rel = str(PurePosixPath(m.name).relative_to(top))
            assert rel in listed, rel
            e = listed[rel]
            assert m.size == e["bytes"]
            data = tar.extractfile(m).read()
            assert digest(data) == e["sha256"], rel
            observed.add(rel)
        assert observed == set(listed)
    print(json.dumps({"archive": str(archive), "archive_sha256": h.hexdigest(),
                      "manifest_sha256": digest(manifest_bytes), "status": manifest["status"],
                      "verified_files": len(observed), "verified_bytes": sum(e["bytes"] for e in listed.values())},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
