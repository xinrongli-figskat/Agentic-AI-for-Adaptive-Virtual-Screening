"""Create a hash-manifested Task1 v4 archive from reviewed delivery files."""
import hashlib
import json
from pathlib import Path
import zipfile


ROOT = Path(__file__).resolve().parents[1]
SOURCES = (
    (ROOT / "outputs/curation_agent_v4", "curation_agent_v4"),
    (ROOT / "outputs/task1_v4_delivery", "task1_v4_delivery"),
)
ARCHIVE = ROOT / "outputs/task1_curation_agent_v4_transfer.zip"
MANIFEST = "TASK1_V4_TRANSFER_MANIFEST.json"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    files = {}
    for source, prefix in SOURCES:
        for path in sorted(source.rglob("*")):
            if path.is_file() and path.suffix != ".zip" and "__pycache__" not in path.parts:
                name = (Path(prefix) / path.relative_to(source)).as_posix()
                data = path.read_bytes()
                files[name] = {"sha256": sha(data), "bytes": len(data), "data": data}
    manifest = {"schema": "task1_v4_transfer_v1", "files": {
        name: {"sha256": item["sha256"], "bytes": item["bytes"]}
        for name, item in files.items()
    }}
    ARCHIVE.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(ARCHIVE, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as bundle:
        for name, item in files.items():
            bundle.writestr(name, item["data"])
        bundle.writestr(MANIFEST, json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    data = ARCHIVE.read_bytes()
    print(json.dumps({"archive": str(ARCHIVE), "sha256": sha(data), "bytes": len(data),
                      "files": len(files), "manifest": MANIFEST}, indent=2))


if __name__ == "__main__":
    main()
