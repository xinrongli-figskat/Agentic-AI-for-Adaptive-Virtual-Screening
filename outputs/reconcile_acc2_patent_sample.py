"""Check a frozen ACC2 source sample against transcribed primary-patent table values.

No GLM, network access, or hidden campaign labels are used. This is deliberately
only a source-value alignment; it does not assert full structure identity.
"""

import argparse
import hashlib
import json
from decimal import Decimal
from pathlib import Path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def reconcile(selection: dict, table: dict) -> dict:
    assert selection["assay_id"] == "CHEMBL3705476"
    source = {item["example"]: item for item in table["values"]}
    assert len(source) == len(table["values"]) == 12
    rows = []
    for signal in ("hit_support", "nonhit_support"):
        members = selection["main_sample"][signal]
        assert len(members) == 6
        for record in members:
            prefix, example = record["compound_name"].split(", ", 1)
            assert prefix == "US8835472"
            patent = source[example]
            chembl_nm = Decimal(str(record["standard_value"]))
            patent_nm = Decimal(patent["ic50_uM"]) * 1000
            match = record["standard_relation"] == "=" and chembl_nm == patent_nm
            rows.append({
                "signal": signal,
                "activity_id": record["activity_id"],
                "molecule_chembl_id": record["molecule_chembl_id"],
                "src_compound_id": record["src_compound_id"],
                "patent_example": example,
                "patent_table_line": patent["line"],
                "patent_ic50_uM": patent["ic50_uM"],
                "chembl_relation": record["standard_relation"],
                "chembl_ic50_nM": str(chembl_nm),
                "numeric_match": match,
            })
    assert len({row["patent_example"] for row in rows}) == 12
    matched = sum(row["numeric_match"] for row in rows)
    return {
        "assay_id": selection["assay_id"],
        "source_url": table["source_url"],
        "sample_count": len(rows),
        "value_matches": matched,
        "value_mismatches": len(rows) - matched,
        "same_source_table": True,
        "assay_method_identified": True,
        "construct_identified": True,
        "molecule_structure_independently_verified": False,
        "source_endpoint_resolved": False,
        "campaign_ready": False,
        "identity_caveat": table["identity_caveat"],
        "rows": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--selection", required=True, type=Path)
    parser.add_argument("--table", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    selection = json.loads(args.selection.read_text(encoding="utf-8"))
    table = json.loads(args.table.read_text(encoding="utf-8"))
    result = reconcile(selection, table)
    args.output_dir.mkdir(parents=True, exist_ok=False)
    (args.output_dir / "alignment.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    receipt = {
        "selection_sha256": sha256(args.selection),
        "transcribed_table_sha256": sha256(args.table),
        "alignment_sha256": sha256(args.output_dir / "alignment.json"),
        "status": "sample_values_aligned_structure_review_pending",
    }
    (args.output_dir / "receipt.json").write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({key: value for key, value in result.items() if key != "rows"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
