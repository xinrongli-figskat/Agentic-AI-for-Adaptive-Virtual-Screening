import csv
import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2] / "outputs"
AUDIT = ROOT / "s_restructure_20261018"
COMPOUND = re.compile(r"^(molecule_chembl_id|compound_chembl_id|molregno|canonical_smiles|compound_id|molecule_id)$", re.I)
MEASUREMENT = re.compile(r"(standard_value|standard_relation|standard_type|pchembl|activity_value|ic50|ec50|ki|kd|label|class_state|provisional_state|hit_support|nonhit_support|activity_comment)", re.I)


def json_has_per_compound_measurement(obj):
    if isinstance(obj, dict):
        keys = [str(k) for k in obj]
        has_compound = any(COMPOUND.match(k) for k in keys)
        has_measurement = any(MEASUREMENT.search(k) for k in keys)
        if has_compound and has_measurement:
            return True
        return any(json_has_per_compound_measurement(v) for v in obj.values())
    if isinstance(obj, list):
        return any(json_has_per_compound_measurement(v) for v in obj)
    return False


def assess(path):
    ext = path.suffix.lower()
    try:
        if ext == ".csv":
            with path.open(encoding="utf-8-sig", errors="replace", newline="") as f:
                header = next(csv.reader(f), [])
            if any(COMPOUND.match(k.strip()) for k in header) and any(MEASUREMENT.search(k.strip()) for k in header):
                return "compound_level_measurement_or_label_columns"
        elif ext in (".json", ".jsonl"):
            text = path.read_text(encoding="utf-8", errors="replace")
            if ext == ".jsonl":
                records = [json.loads(line) for line in text.splitlines() if line.strip()]
                found = any(json_has_per_compound_measurement(x) for x in records)
            else:
                found = json_has_per_compound_measurement(json.loads(text))
            if found:
                return "compound_level_measurement_or_label_objects"
        elif ext == ".zip":
            import zipfile
            with zipfile.ZipFile(path) as zf:
                for name in zf.namelist():
                    if Path(name).suffix.lower() not in (".csv", ".json", ".jsonl"):
                        continue
                    data = zf.read(name)
                    try:
                        if Path(name).suffix.lower() == ".csv":
                            header = next(csv.reader(data.decode("utf-8-sig", "replace").splitlines()), [])
                            if any(COMPOUND.match(k.strip()) for k in header) and any(MEASUREMENT.search(k.strip()) for k in header):
                                return "archive_contains_compound_level_measurements"
                        else:
                            text = data.decode("utf-8", "replace")
                            obj = json.loads(text) if not name.endswith(".jsonl") else [json.loads(x) for x in text.splitlines() if x.strip()]
                            if json_has_per_compound_measurement(obj):
                                return "archive_contains_compound_level_measurements"
                    except Exception:
                        continue
    except Exception as e:
        return "scan_error_" + type(e).__name__
    return "no_compound_level_label_schema_detected"


def main():
    grouped = {}
    labeled_paths = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or AUDIT in path.parents:
            continue
        private_name = any("private" in p.name.lower() for p in path.parents)
        reverse_scan = not private_name
        result = assess(path)
        parts = path.relative_to(ROOT).parts
        if private_name:
            if parts[0] == "private":
                group_path = f"private/{parts[1]}" if len(parts) > 1 else "private"
            else:
                privacy_dir = next((p for p in parts[:-1] if "private" in p.lower()), parts[0])
                group_path = privacy_dir
        elif result != "no_compound_level_label_schema_detected":
            group_path = parts[0]
        else:
            continue
        group = grouped.setdefault(group_path, {
            "path_group": group_path,
            "private_named_path": str(private_name).lower(),
            "reverse_scan_nonprivate": str(reverse_scan).lower(),
            "files_scanned": 0,
            "compound_level_label_files": 0,
            "archive_label_data_files": 0,
            "scan_errors": 0,
        })
        group["files_scanned"] += 1
        if result.startswith("compound_level"):
            group["compound_level_label_files"] += 1
        elif result.startswith("archive_contains"):
            group["archive_label_data_files"] += 1
        elif result.startswith("scan_error"):
            group["scan_errors"] += 1
        if result.startswith("compound_level") or result.startswith("archive_contains"):
            labeled_paths.append((path.relative_to(ROOT.parent).as_posix(), group_path))
    ignored = subprocess.run(
        ["git", "check-ignore", "--stdin", "--no-index", "-z"],
        cwd=ROOT.parent,
        input="\0".join(path for path, _ in labeled_paths) + "\0",
        text=True,
        capture_output=True,
        check=False,
    ).stdout.split("\0")
    ignored_set = set(ignored)
    for path, group_path in labeled_paths:
        group = grouped[group_path]
        is_ignored = path in ignored_set
        group["git_ignored_label_files"] = group.get("git_ignored_label_files", 0) + int(is_ignored)
        group["git_unignored_label_files"] = group.get("git_unignored_label_files", 0) + int(not is_ignored)
    rows = list(grouped.values())
    out = AUDIT / "s6_private_audit.csv"
    with out.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["path_group", "private_named_path", "reverse_scan_nonprivate", "files_scanned", "compound_level_label_files", "archive_label_data_files", "git_ignored_label_files", "git_unignored_label_files", "scan_errors"])
        writer.writeheader()
        writer.writerows(rows)
    dirs = {r["path_group"]: r["compound_level_label_files"] + r["archive_label_data_files"] for r in rows if r["compound_level_label_files"] or r["archive_label_data_files"]}
    print("audited_files=", sum(1 for p in ROOT.rglob("*") if p.is_file() and AUDIT not in p.parents))
    print("reported_paths=", len(rows))
    print("label_bearing_top_level_dirs=", json.dumps(dirs, ensure_ascii=False, sort_keys=True))
    print("report=", out)


if __name__ == "__main__":
    main()
