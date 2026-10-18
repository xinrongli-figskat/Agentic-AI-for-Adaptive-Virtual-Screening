"""Select up to four Table 3 source rows under the locked v5 hash rule."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixed-selection", type=Path, required=True)
    parser.add_argument("--expected-fixed-selection-sha256", required=True)
    parser.add_argument("--full-mapping", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    selection_bytes = args.fixed_selection.read_bytes()
    if sha256(selection_bytes) != args.expected_fixed_selection_sha256.lower():
        raise ValueError("Locked fixed-selection hash mismatch")
    fixed = json.loads(selection_bytes)
    already = {item["molecule_chembl_id"] for item in fixed["sample"]["selected"]}
    mapping_bytes = args.full_mapping.read_bytes()
    mapping = json.loads(mapping_bytes)
    if mapping["assay_id"] != "CHEMBL5734042" or mapping["source_molecule_count"] != 294:
        raise ValueError("Unexpected full source mapping")
    choices = []
    for item in mapping["rows"]:
        if item["status"] != "matched_table_3" or item["molecule_chembl_id"] in already:
            continue
        for activity_id in item["activity_ids"]:
            sort_hash = sha256(("task1-v5-source-audit|" + str(activity_id)).encode())
            choices.append((sort_hash, activity_id, item))
    choices.sort(key=lambda row: (row[0], row[1]))
    chosen = []
    selected_ids = set()
    for sort_hash, activity_id, item in choices:
        if item["molecule_chembl_id"] in selected_ids:
            continue
        selected_ids.add(item["molecule_chembl_id"])
        chosen.append({"sort_sha256": sort_hash, "activity_id": activity_id,
                       "molecule_chembl_id": item["molecule_chembl_id"],
                       "pubchem_cid": item["pubchem_cid"],
                       "patent_examples": item["pubchem_examples"],
                       "chembl_measurements": item["chembl_measurements"],
                       "matching_grant_table_rows": item["matching_grant_table_rows"]})
        if len(chosen) == 4:
            break
    if len(chosen) < 2:
        raise ValueError("Insufficient confirmed Table 3 matches under locked rule")
    report = {"schema": "task1_v5_s1pr1_table3_supplement_v1",
              "selection_rule": "SHA256('task1-v5-source-audit|' + activity_id), first four distinct Table 3 source IDs not in the fixed 12",
              "fixed_selection_sha256": sha256(selection_bytes),
              "full_mapping_sha256": sha256(mapping_bytes),
              "eligible_table3_source_ids": len({r[2]["molecule_chembl_id"] for r in choices}),
              "selected": chosen, "status": "table3_supplement_selected_for_manual_source_review",
              "campaign_ready": False}
    data = (json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists():
        if args.output.read_bytes() != data:
            raise FileExistsError("Existing supplement selection differs; do not overwrite")
    else:
        with args.output.open("xb") as handle:
            handle.write(data)
    print(json.dumps({"eligible_table3": report["eligible_table3_source_ids"],
                      "selected": [(r["activity_id"], r["molecule_chembl_id"],r["patent_examples"]) for r in chosen],
                      "report_sha256": sha256(data), "output": str(args.output)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
