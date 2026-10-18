"""Verify and install the Task1 v4 transfer archive into new project directories."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import tempfile
import zipfile


MANIFEST = "TASK1_V4_TRANSFER_MANIFEST.json"
ALLOWED_ROOTS = {"curation_agent_v4", "task1_v4_delivery"}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def safe_name(name):
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise ValueError("Unsafe archive member path: " + name)
    if path.parts[0] not in ALLOWED_ROOTS:
        raise ValueError("Unexpected archive root: " + name)
    return path


def install(archive, root):
    archive = Path(archive).resolve()
    root = Path(root).resolve()
    package_dirs = [root / name for name in sorted(ALLOWED_ROOTS)]
    if not (root / "curation_agent_v3").is_dir():
        raise ValueError("Install the new package beside the existing curation_agent_v3 directory")
    receipt = root / ".task1_v4_install.json"
    if receipt.exists():
        saved = json.loads(receipt.read_text(encoding="utf-8"))
        if saved.get("archive_sha256") != digest(archive.read_bytes()):
            raise ValueError("An install receipt exists for a different archive; no files changed")
        return {"status": "already_installed_identical", "receipt": str(receipt)}
    present = [path.exists() for path in package_dirs]
    if any(present):
        raise ValueError("A destination package directory already exists; no files changed")

    with zipfile.ZipFile(archive, "r") as bundle:
        names = bundle.namelist()
        if len(names) != len(set(names)) or MANIFEST not in names:
            raise ValueError("Archive has duplicate members or no manifest")
        manifest = json.loads(bundle.read(MANIFEST).decode("utf-8"))
        expected = manifest.get("files")
        if not isinstance(expected, dict) or set(names) != set(expected) | {MANIFEST}:
            raise ValueError("Archive members do not match the manifest")
        payload = {}
        for name, metadata in expected.items():
            safe_name(name)
            info = bundle.getinfo(name)
            if (info.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError("Symbolic links are not allowed in the transfer archive")
            data = bundle.read(name)
            if len(data) != metadata.get("bytes") or digest(data) != metadata.get("sha256"):
                raise ValueError("Member hash/size mismatch: " + name)
            payload[name] = data

    stage = Path(tempfile.mkdtemp(prefix=".task1_v4_stage_", dir=root))
    try:
        for name, data in payload.items():
            target = stage.joinpath(*PurePosixPath(name).parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        for name in sorted(ALLOWED_ROOTS):
            (stage / name).replace(root / name)
    finally:
        if stage.exists():
            # Only remove the installer-created staging directory after successful moves.
            try:
                stage.rmdir()
            except OSError:
                pass
    record = {"status": "installed_verified_new_directories", "archive": archive.name,
              "archive_sha256": digest(archive.read_bytes()), "files": len(payload),
              "directories": sorted(ALLOWED_ROOTS)}
    receipt.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    print(json.dumps(install(args.archive, args.root), indent=2))


if __name__ == "__main__":
    main()
