"""Audit IC50 value resolution in curated ChEMBL 37 assays without using an LLM.

This is a source-review triage signal. Repeated values do not by themselves prove
that an importer substituted category midpoints for measurements.
"""
from __future__ import annotations

import argparse
from collections import Counter
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path


def canonical_key(row: dict) -> tuple[str, str, str]:
    relation = str(row.get("standard_relation") or "<missing>")
    unit = str(row.get("standard_units") or "<missing>")
    try:
        value = str(Decimal(str(row.get("standard_value"))).normalize())
    except (InvalidOperation, ValueError):
        value = "<missing>"
    return relation, value, unit


def summarize_records(records: list[dict]) -> dict:
    counts = Counter(canonical_key(row) for row in records)
    common = [
        {"relation": key[0], "value": key[1], "unit": key[2], "records": count}
        for key, count in counts.most_common(10)
    ]
    total = len(records)
    distinct = len(counts)
    return {
        "record_count": total,
        "distinct_relation_value_unit": distinct,
        "largest_value_fraction": counts.most_common(1)[0][1] / total if total else 0.0,
        "top_values": common,
        "low_resolution_review_flag": total >= 250 and distinct <= 8,
        "note": "A flag requests primary-source review; it is not an automatic rejection.",
    }


def load_verified(folder: Path, name: str):
    hashes = json.loads((folder / "file_hashes.json").read_text(encoding="utf-8"))
    path = folder / name
    expected = hashes[name]
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != expected:
        raise ValueError(f"Hash mismatch: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def run(roots: list[Path], output: Path) -> dict:
    assays = {}
    for root in roots:
        for folder in sorted(root.glob("CHEMBL*")):
            if not folder.is_dir():
                continue
            assay_id = folder.name
            if assay_id in assays:
                raise ValueError(f"Duplicate assay: {assay_id}")
            summary = load_verified(folder, "summary.json")
            records = load_verified(folder, "source_records.json")
            if summary["assay_id"] != assay_id or len(records) != summary["record_count"]:
                raise ValueError(f"Assay identity or record count mismatch: {assay_id}")
            assays[assay_id] = {
                "assay_id": assay_id,
                "target_id": summary["target_id"],
                "numeric_pass": summary["qualification"].get("numerical_eligibility") is True,
                **summarize_records(records),
            }
    if len(assays) != 81:
        raise ValueError(f"Expected 81 audited assays, found {len(assays)}")
    ordered = sorted(assays.values(), key=lambda x: (
        not x["numeric_pass"], not x["low_resolution_review_flag"],
        x["distinct_relation_value_unit"], -x["record_count"], x["assay_id"]))
    result = {
        "purpose": "value_resolution_source_review_triage_only",
        "assays_audited": len(ordered),
        "numeric_pass_assays": sum(bool(x["numeric_pass"]) for x in ordered),
        "low_resolution_review_flags": sum(x["low_resolution_review_flag"] for x in ordered),
        "low_resolution_numeric_pass_flags": sum(
            x["low_resolution_review_flag"] and x["numeric_pass"] for x in ordered),
        "assays": ordered,
        "campaign_ready": False,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, action="append", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.root, args.out)
    print(json.dumps({key: value for key, value in result.items() if key != "assays"}, indent=2))


if __name__ == "__main__":
    main()
