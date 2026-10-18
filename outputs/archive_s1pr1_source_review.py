"""Create a checked, append-only archive of the S1PR1 source-review workspace."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path
import zipfile


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source = args.source.resolve(strict=True)
    output = args.output.resolve()
    if source in output.parents:
        raise ValueError("Archive must be outside the source directory")
    paths = sorted(path for path in source.rglob("*") if path.is_file())
    manifest = {path.relative_to(source).as_posix(): {"sha256": digest(path.read_bytes()), "size": path.stat().st_size}
                for path in paths}
    if "manifest.json" in manifest:
        raise ValueError("Source contains reserved manifest name")
    manifest_bytes = (json.dumps({"schema": "s1pr1_source_review_archive_v1", "files": manifest},
                                 sort_keys=True, indent=2) + "\n").encode()
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in paths:
            name = path.relative_to(source).as_posix()
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
        info = zipfile.ZipInfo("manifest.json", date_time=(1980, 1, 1, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        archive.writestr(info, manifest_bytes, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    data = buffer.getvalue()
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        if output.read_bytes() != data:
            raise FileExistsError("Existing archive differs")
    else:
        output.write_bytes(data)
    print(json.dumps({"file_count": len(paths), "archive_sha256": digest(data),
                      "archive_bytes": len(data), "manifest_sha256": digest(manifest_bytes),
                      "output": str(output)}, indent=2))


if __name__ == "__main__":
    main()
