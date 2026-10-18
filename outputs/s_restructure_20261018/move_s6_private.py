import csv
import hashlib
import shutil
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs"
SOURCE = OUT / "r4_source_review_private_20261018"
DESTINATION = OUT / "private" / SOURCE.name
MAPPING = OUT / "PATH_MIGRATION_20261018.csv"


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    if not SOURCE.is_dir() or DESTINATION.exists():
        raise SystemExit("Expected private source dir or destination state changed; refusing to move")
    files = sorted(p for p in SOURCE.rglob("*") if p.is_file())
    entries = [(p, digest(p)) for p in files]
    shutil.move(str(SOURCE), str(DESTINATION))
    for original, expected in entries:
        target = DESTINATION / original.relative_to(SOURCE)
        if digest(target) != expected:
            raise SystemExit(f"SHA-256 mismatch: {target}")
    exists = MAPPING.exists()
    with MAPPING.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["old_relative_path", "new_relative_path", "sha256", "moved_utc", "task_card"])
        if not exists:
            writer.writeheader()
        now = datetime.now(timezone.utc).isoformat()
        for original, expected in entries:
            writer.writerow({
                "old_relative_path": original.relative_to(OUT).as_posix(),
                "new_relative_path": (DESTINATION / original.relative_to(SOURCE)).relative_to(OUT).as_posix(),
                "sha256": expected,
                "moved_utc": now,
                "task_card": "S6",
            })
    print(f"moved_files={len(entries)}")
    print("sha256_all_match=true")
    print(f"destination={DESTINATION}")


if __name__ == "__main__":
    main()
