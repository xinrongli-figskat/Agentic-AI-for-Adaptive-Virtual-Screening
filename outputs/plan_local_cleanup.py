"""Plan regenerable or verified duplicate cleanup; this tool never deletes."""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import uuid
import zipfile

ROOT = Path(__file__).resolve().parent.parent
REGENERABLE = [
    ".cache/pip", ".cache/pip-audit", ".cache/curation-check-pip",
    ".cache/task1_import_validation", ".cache/task1_import_validation_final",
    ".cache/task1_review_replay", ".cache/task1_v2_final_prepare",
    ".cache/task1_v2_offline_prepare", ".cache/task1_v2_validated_prepare",
    ".cache/report_synthetic_validation_6cd3d3ee", ".cache/task1_v3_prerelease_20261016",
    "outputs/task1_v3_replay_validation", "outputs/task1_v3_replay_validation_final",
    "outputs/task1_v3_replay_delivery_validation",
]
STAGING = ["outputs/next_stage_transfer", "outputs/source_alignment_review_20261015",
           "outputs/assay_audit_transfer_20261014", "outputs/assay_review_transfer_20261014"]
DUPLICATE_BACKUP = ".sync_audit/backup_20261015_bbea8ee9/backup_20261015_bbea8ee9_local_snapshot.zip"
CANONICAL_BACKUP = ".sync_audit/backup_20261015_bbea8ee9/local_snapshot.zip"


def sha(path):
    result = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def all_files():
    files = {}
    for parent, dirs, names in os.walk(ROOT, followlinks=False):
        for name in dirs + names:
            path = Path(parent) / name
            if getattr(path.lstat(), "st_file_attributes", 0) & 0x400 or path.is_symlink():
                raise ValueError("Reparse point or symbolic link requires separate review: " + str(path))
        for name in names:
            path = Path(parent) / name
            files[path.relative_to(ROOT).as_posix()] = {"bytes": path.stat().st_size, "sha256": sha(path)}
    return files


def main():
    before = all_files()
    archive_index = {}
    for relative, item in before.items():
        if not relative.lower().endswith(".zip") or relative.startswith(".cache/") or relative == DUPLICATE_BACKUP:
            continue
        with zipfile.ZipFile(ROOT / relative) as bundle:
            for entry in bundle.infolist():
                if not entry.is_dir():
                    value = hashlib.sha256(bundle.read(entry)).hexdigest()
                    archive_index.setdefault(value, {"archive": relative, "member": entry.filename,
                        "archive_sha256": item["sha256"]})
    candidates, skipped = [], []

    def add(relative, category, recovery, proofs=None):
        members = {name: item for name, item in before.items()
                   if name == relative or name.startswith(relative + "/")}
        if members:
            candidates.append({"relative_path": relative, "kind": "directory" if (ROOT / relative).is_dir() else "file",
                "category": category, "recovery": recovery, "files": members,
                "bytes": sum(item["bytes"] for item in members.values()), "archive_proofs": proofs or {}})

    for relative in REGENERABLE:
        if relative.startswith(".cache/pip") or relative == ".cache/curation-check-pip":
            add(relative, "package_download_cache",
                "Redownload package caches when needed; installed scientific libraries remain in place.")
        else:
            add(relative, "temporary_validation_copy",
                "Regenerate from retained source, actual-run evidence and final validation/replay. Never-delivered prerelease copies are not required for delivered versions.")
    if DUPLICATE_BACKUP in before:
        if before[DUPLICATE_BACKUP]["sha256"] != before[CANONICAL_BACKUP]["sha256"]:
            raise ValueError("Backup candidate is not byte-identical to the retained canonical backup")
        add(DUPLICATE_BACKUP, "identical_backup_copy", "Copy retained canonical backup: " + CANONICAL_BACKUP)
    for relative in STAGING:
        members = {name: item for name, item in before.items() if name.startswith(relative + "/")}
        missing = [name for name, item in members.items() if item["sha256"] not in archive_index]
        if missing:
            skipped.append({"relative_path": relative, "reason": "No verified retained ZIP copy for some files",
                            "unmatched_files": missing})
        else:
            proofs = {name: archive_index[item["sha256"]] for name, item in members.items()}
            add(relative, "verified_archived_staging_copy",
                "Restore exact bytes from the retained ZIP/member recorded for each file.", proofs)
    selected = {name for candidate in candidates for name in candidate["files"]}
    for name in sorted(before):
        if (name not in selected and name.endswith(".pyc") and "/__pycache__/" in "/" + name
                and (name.startswith(".cache/") or name.startswith("outputs/"))
                and not name.startswith("outputs/results/")):
            add(name, "python_bytecode_cache", "Python regenerates bytecode from retained .py source.")
            selected.add(name)
    protected = {name: value for name, value in before.items() if name not in selected}
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report_dir = ROOT / ".sync_audit" / ("cleanup_" + stamp + "_" + uuid.uuid4().hex[:8])
    report_dir.mkdir()
    write(report_dir / "preserved_files.json", protected)
    plan = {"schema": "project_cleanup_v1", "project_root": str(ROOT), "status": "planned_no_deletions",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "before_file_count": len(before), "before_bytes": sum(item["bytes"] for item in before.values()),
        "delete_file_count": len(selected), "delete_bytes": sum(before[name]["bytes"] for name in selected),
        "candidates": candidates, "skipped": skipped,
        "preserved_manifest": str(report_dir / "preserved_files.json"),
        "preserved_manifest_sha256": sha(report_dir / "preserved_files.json"),
        "notes": "Retain core code, installed libraries, actual-run evidence, source documents, final reports/replay, canonical backups and transfer ZIPs. Downloads/Desktop inspected separately."}
    write(report_dir / "plan.json", plan)
    totals = Counter()
    for candidate in candidates:
        totals[candidate["category"]] += candidate["bytes"]
    print(json.dumps({"plan": str(report_dir / "plan.json"), "plan_sha256": sha(report_dir / "plan.json"),
        "before_bytes": plan["before_bytes"], "delete_bytes": plan["delete_bytes"],
        "delete_file_count": plan["delete_file_count"], "bytes_by_category": dict(totals), "skipped": skipped},
        ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
