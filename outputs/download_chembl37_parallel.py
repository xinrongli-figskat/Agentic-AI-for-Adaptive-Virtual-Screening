"""Resume official ChEMBL 37 SQLite with bounded HTTP ranges and SHA-256."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import shutil
import time
from urllib.request import Request, urlopen


URL = "https://ftp.ebi.ac.uk/pub/databases/chembl/ChEMBLdb/releases/chembl_37/chembl_37_sqlite.tar.gz"
EXPECTED = "33c203740555f96067710cdfc1c3c55d890660e5908ec5cbf5817492c290d281"


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(16 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write_once(path: Path, data: bytes) -> None:
    if path.exists():
        if path.read_bytes() != data:
            raise FileExistsError(f"Existing file differs: {path}")
    else:
        with path.open("xb") as stream:
            stream.write(data)


def download_part(folder: Path, item: dict, etag: str, total: int) -> dict:
    path = folder / f"part_{item['index']:02d}.bin"
    required = item["end"] - item["start"] + 1
    for attempt in range(8):
        have = path.stat().st_size if path.exists() else 0
        if have == required:
            return {"index": item["index"], "bytes": have, "sha256": digest(path)}
        if have > required:
            raise ValueError(f"Part {item['index']} exceeds its declared range")
        first = item["start"] + have
        request = Request(URL, headers={"Range": f"bytes={first}-{item['end']}",
                                        "If-Range": etag, "User-Agent": "agentic-screening-chembl37/1.0"})
        try:
            with urlopen(request, timeout=60) as response:
                expected_range = f"bytes {first}-{item['end']}/{total}"
                if response.status != 206 or response.headers.get("Content-Range") != expected_range:
                    raise ValueError(f"Range response mismatch for part {item['index']}")
                with path.open("ab") as output:
                    while True:
                        block = response.read(1024 * 1024)
                        if not block:
                            break
                        output.write(block)
            if path.stat().st_size == required:
                return {"index": item["index"], "bytes": required, "sha256": digest(path)}
        except (OSError, TimeoutError) as error:
            print(json.dumps({"part": item["index"], "attempt": attempt + 1,
                              "error": str(error)}), flush=True)
            time.sleep(min(20, attempt * 3 + 1))
    raise RuntimeError(f"Part {item['index']} failed after retries")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    folder = args.directory.resolve()
    if not 1 <= args.workers <= 8:
        raise ValueError("Worker count must be 1-8")
    checksum_text = (folder / "checksums.txt").read_text()
    if not any(line.split() == [EXPECTED, "chembl_37_sqlite.tar.gz"] for line in checksum_text.splitlines()):
        raise ValueError("Official checksum text does not match expected release")
    destination = folder / "chembl_37_sqlite.tar.gz"
    receipt = folder / "download_verified.json"
    if receipt.exists() and destination.exists() and digest(destination) == EXPECTED:
        print(json.dumps({"status": "already_verified", "sha256": EXPECTED}), flush=True)
        return
    if receipt.exists():
        raise ValueError("Verified receipt exists but archive is missing or altered")
    head = Request(URL, method="HEAD", headers={"User-Agent": "agentic-screening-chembl37/1.0"})
    with urlopen(head, timeout=30) as response:
        total = int(response.headers["Content-Length"])
        etag = response.headers["ETag"]
        if response.status != 200 or total != 5764252857:
            raise ValueError("Unexpected release size or HEAD response")
    prefix = folder / "prefix.part"
    if destination.exists() and not prefix.exists():
        destination.rename(prefix)
    if not prefix.exists() or not 0 < prefix.stat().st_size < total:
        raise ValueError("Expected an incomplete verified-source prefix")
    manifest_path = folder / "segments_manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_bytes())
        if manifest["prefix_sha256"] != digest(prefix) or manifest["prefix_bytes"] != prefix.stat().st_size:
            raise ValueError("Prefix differs from frozen segment manifest")
        if manifest["total_bytes"] != total or manifest["etag"] != etag:
            raise ValueError("Official release headers changed")
        parts = manifest["parts"]
    else:
        start = prefix.stat().st_size
        remaining = total - start
        parts = []
        for index in range(args.workers):
            first = start + remaining * index // args.workers
            last = start + remaining * (index + 1) // args.workers - 1
            parts.append({"index": index, "start": first, "end": last})
        manifest = {"schema": "chembl37_official_range_transfer_v1", "url": URL,
                    "total_bytes": total, "etag": etag, "expected_sha256": EXPECTED,
                    "prefix_bytes": start, "prefix_sha256": digest(prefix), "parts": parts}
        write_once(manifest_path, (json.dumps(manifest, sort_keys=True, indent=2) + "\n").encode())
    print(json.dumps({"status": "downloading_ranges", "prefix_bytes": manifest["prefix_bytes"],
                      "workers": len(parts), "total_bytes": total}), flush=True)
    with ThreadPoolExecutor(max_workers=len(parts)) as pool:
        completed = list(pool.map(lambda item: download_part(folder, item, etag, total), parts))
    print(json.dumps({"status": "ranges_complete", "parts": completed}), flush=True)
    assembled = folder / "assembled.tmp"
    if assembled.exists():
        raise FileExistsError("Existing assembled.tmp requires inspection before retry")
    h = hashlib.sha256()
    with assembled.open("xb") as output:
        for path in [prefix] + [folder / f"part_{item['index']:02d}.bin" for item in parts]:
            with path.open("rb") as source:
                while True:
                    block = source.read(16 * 1024 * 1024)
                    if not block:
                        break
                    output.write(block)
                    h.update(block)
    actual = h.hexdigest()
    if assembled.stat().st_size != total or actual != EXPECTED:
        raise ValueError(f"Assembled archive checksum failed: {actual}")
    os.replace(assembled, destination)
    write_once(receipt, (json.dumps({"status": "verified", "archive_sha256": actual,
                                    "archive_bytes": total, "transfer_manifest_sha256": digest(manifest_path)},
                                   sort_keys=True, indent=2) + "\n").encode())
    print(json.dumps({"status": "verified", "archive_sha256": actual, "archive_bytes": total}), flush=True)


if __name__ == "__main__":
    main()
