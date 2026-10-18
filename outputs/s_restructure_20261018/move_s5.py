import csv
import hashlib
import shutil
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs"
TASK = "S5"
MAPPING = OUT / "PATH_MIGRATION_20261018.csv"


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def expand_move(src: Path, dst: Path):
    if src.is_file():
        return [(src, dst)]
    if not src.is_dir():
        raise FileNotFoundError(src)
    pairs = []
    for path in sorted(src.rglob("*")):
        if path.is_file():
            pairs.append((path, dst / path.relative_to(src)))
    if not pairs:
        raise RuntimeError(f"Refusing to move empty directory: {src}")
    return pairs


def main():
    with (OUT / "s_restructure_20261018" / "script_classification.csv").open(
        newline="", encoding="utf-8-sig"
    ) as f:
        scripts = list(csv.DictReader(f))
    pairs = []
    for row in scripts:
        if row["move_decision"] == "move_candidate":
            src = OUT / Path(row["source"]).name
            dst = ROOT / row["destination"]
            pairs.extend(expand_move(src, dst))

    planned = [
        (OUT / "benchmark_build_progress_20261017.md", OUT / "brief" / "benchmark_build_progress_20261017.md"),
        (OUT / "brief_progress_review_20261018", OUT / "brief" / "brief_progress_review_20261018"),
        (OUT / "q2_decision_draft_20261018", OUT / "brief" / "q2_decision_draft_20261018"),
        (OUT / "lab-4090.ssh_config", OUT / "env" / "lab-4090.ssh_config"),
    ]
    for src, dst in planned:
        pairs.extend(expand_move(src, dst))

    sources = [s.resolve() for s, _ in pairs]
    destinations = [d.resolve() for _, d in pairs]
    if len(sources) != len(set(sources)):
        raise RuntimeError("Duplicate source in move plan")
    if len(destinations) != len(set(destinations)):
        raise RuntimeError("Destination collision in move plan")
    for src, dst in pairs:
        if not src.is_file() or dst.exists():
            raise RuntimeError(f"Unsafe/missing source or existing destination: {src} -> {dst}")
        if not src.resolve().is_relative_to(OUT.resolve()):
            raise RuntimeError(f"Source outside outputs: {src}")
        if not dst.resolve().is_relative_to(OUT.resolve()):
            raise RuntimeError(f"Destination outside outputs: {dst}")

    entries = []
    for src, dst in pairs:
        digest = sha(src)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
        if sha(dst) != digest:
            raise RuntimeError(f"Hash mismatch after move: {src} -> {dst}")
        entries.append({
            "old_path": src.relative_to(ROOT).as_posix(),
            "new_path": dst.relative_to(ROOT).as_posix(),
            "sha256": digest,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "task": TASK,
        })

    # Remove only empty source directories left by these file moves.
    for src, _ in reversed(planned):
        if src.is_dir():
            for directory in sorted((p for p in src.rglob("*") if p.is_dir()), reverse=True):
                try:
                    directory.rmdir()
                except OSError:
                    pass
            try:
                src.rmdir()
            except OSError:
                pass

    exists = MAPPING.exists()
    with MAPPING.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["old_path", "new_path", "sha256", "timestamp_utc", "task"])
        if not exists:
            writer.writeheader()
        writer.writerows(entries)
    print(f"moved_files={len(entries)}")
    print(f"all_hashes_verified=true")
    for entry in entries:
        print(f"{entry['old_path']} -> {entry['new_path']} {entry['sha256']}")


if __name__ == "__main__":
    main()
