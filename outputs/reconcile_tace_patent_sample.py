"""Reconcile the fixed TACE source sample against patent Table VIII values.

This does not independently validate chemical structure identity or approve a
benchmark. It compares the primary patent's example numbers and IC50 reports.
"""
from __future__ import annotations

import argparse
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def example_numbers(compound_name: str) -> list[int]:
    pieces = compound_name.split("::")
    numbers = []
    for piece in pieces:
        match = re.fullmatch(r"US9926281, Compound (\d+)", piece)
        if not match:
            raise ValueError(f"Unexpected source compound name: {compound_name}")
        numbers.append(int(match.group(1)))
    return sorted(numbers)


def reconcile(selection: dict, table: dict) -> dict:
    if selection["assay_id"] != table["assay_id"] or table["assay_id"] != "CHEMBL5733557":
        raise ValueError("Assay mismatch")
    source = {item["activity_id"]: item for item in table["source_values"]}
    if len(source) != len(table["source_values"]) or len(source) != 12:
        raise ValueError("Expected 12 distinct source-value entries")
    rows = []
    for signal in ("hit_support", "nonhit_support"):
        members = selection["main_sample"][signal]
        if len(members) != 6:
            raise ValueError(f"Incomplete fixed sample: {signal}")
        for record in members:
            patent = source[record["activity_id"]]
            names_match = example_numbers(record["compound_name"]) == sorted(patent["compound_numbers"])
            values_match = (record["standard_relation"] == patent["relation"]
                            and record["standard_units"] == "nM"
                            and Decimal(str(record["standard_value"])) == Decimal(patent["value_nM"]))
            rows.append({
                "signal": signal,
                "activity_id": record["activity_id"],
                "molecule_chembl_id": record["molecule_chembl_id"],
                "compound_numbers": patent["compound_numbers"],
                "patent_lines": patent["lines"],
                "patent_relation": patent["relation"],
                "patent_value_nM": patent["value_nM"],
                "chembl_relation": record["standard_relation"],
                "chembl_value_nM": str(record["standard_value"]),
                "source_name_match": names_match,
                "value_match": values_match,
            })
    if set(source) != {r["activity_id"] for r in rows}:
        raise ValueError("Source table and fixed sample IDs differ")
    return {
        "assay_id": selection["assay_id"],
        "source_url": table["source_url"],
        "source_table": table["source_table"],
        "sample_count": len(rows),
        "name_matches": sum(r["source_name_match"] for r in rows),
        "value_matches": sum(r["value_match"] for r in rows),
        "assay_method_identified": True,
        "compound_structures_independently_verified": False,
        "source_endpoint_resolved": False,
        "campaign_ready": False,
        "identity_caveat": table["identity_caveat"],
        "rows": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--table", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    selection = json.loads(args.selection.read_text(encoding="utf-8"))
    table = json.loads(args.table.read_text(encoding="utf-8"))
    result = reconcile(selection, table)
    args.output_dir.mkdir(parents=True, exist_ok=False)
    alignment = args.output_dir / "alignment.json"
    alignment.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    receipt = {
        "selection_sha256": sha256(args.selection),
        "transcribed_table_sha256": sha256(args.table),
        "alignment_sha256": sha256(alignment),
        "status": "sample_names_and_values_aligned_structure_review_pending",
    }
    (args.output_dir / "receipt.json").write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "rows"}, indent=2))


if __name__ == "__main__":
    main()
