"""Map archived assay measurements to grant patent Tables 2/3 by source names."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
import zipfile


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parse_patent_value(raw: str) -> tuple[str, Decimal] | None:
    text = raw.strip()
    if not text or text in ("—", "–", "-", "��"):
        return None
    relation = ">" if text.startswith(">") else "<" if text.startswith("<") else "="
    if relation != "=":
        text = text[1:]
    try:
        return relation, Decimal(text)
    except InvalidOperation:
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--expected-archive-sha256", required=True)
    parser.add_argument("--patent-tables", type=Path, required=True)
    parser.add_argument("--pubchem-receipts", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    archive_bytes = args.archive.read_bytes()
    archive_hash = sha256(archive_bytes)
    if archive_hash != args.expected_archive_sha256.lower():
        raise ValueError("Archived v4 hash mismatch")
    with zipfile.ZipFile(args.archive) as archive:
        window_bytes = archive.read("run/evidence/E0174_thin_target_window.json")
    assay_rows = [r for r in json.loads(window_bytes)["records"]
                  if r["assay_chembl_id"] == "CHEMBL5734042"]
    by_molecule = defaultdict(list)
    for row in assay_rows:
        by_molecule[row["molecule_chembl_id"]].append(row)
    if len(assay_rows) != 295 or len(by_molecule) != 294:
        raise ValueError("Archived assay counts changed")
    patent_bytes = args.patent_tables.read_bytes()
    patent = json.loads(patent_bytes)
    examples = defaultdict(list)
    for table in patent["tables"]:
        for row in table["rows"]:
            examples[row["example"]].append({"table": table["table"], "label": row["example_label"],
                                              "s1pr1_value_um": row["s1pr1_aa_ic50_um"]})
    summary = Counter()
    mapped = []
    receipt_hashes = []
    for molecule_id, records in sorted(by_molecule.items()):
        path = args.pubchem_receipts / (molecule_id + ".json")
        if not path.exists():
            mapped.append({"molecule_chembl_id": molecule_id, "status": "pubchem_receipt_missing"})
            summary["pubchem_receipt_missing"] += 1
            continue
        receipt_bytes = path.read_bytes()
        receipt_hashes.append([molecule_id, sha256(receipt_bytes)])
        receipt = json.loads(receipt_bytes)
        if receipt["molecule_chembl_id"] != molecule_id or receipt["archive_sha256"] != archive_hash:
            raise ValueError(f"PubChem receipt source mismatch: {molecule_id}")
        source = receipt.get("parsed") or {}
        names = source.get("patent_example_candidates") or []
        example_ids = sorted({name.split()[0] for name in names})
        if receipt["http_status"] != 200 or len(example_ids) != 1:
            status = "pubchem_name_unresolved_or_ambiguous"
            matches = []
        else:
            candidates = examples.get(example_ids[0], [])
            matches = []
            for candidate in candidates:
                patent_value = parse_patent_value(candidate["s1pr1_value_um"])
                if patent_value is None:
                    continue
                relation, value = patent_value
                compatible = all(record["standard_units"] == "nM"
                                 and record["standard_relation"] == relation
                                 and Decimal(str(record["standard_value"])) == value * 1000
                                 for record in records)
                if compatible:
                    matches.append(candidate)
            if len(matches) == 1:
                status = f"matched_table_{matches[0]['table']}"
            elif len(matches) > 1:
                status = "matched_multiple_tables"
            else:
                status = "no_matching_patent_s1pr1_value"
        summary[status] += 1
        mapped.append({"molecule_chembl_id": molecule_id,
                       "activity_ids": [r["activity_id"] for r in records],
                       "chembl_measurements": [{"relation": r["standard_relation"],
                                                "value": r["standard_value"], "units": r["standard_units"]}
                                               for r in records],
                       "pubchem_cid": source.get("cid"), "pubchem_examples": names,
                       "all_grant_table_candidates": examples.get(example_ids[0], []) if len(example_ids) == 1 else [],
                       "matching_grant_table_rows": matches, "status": status})
    report = {"schema": "s1pr1_full_assay_grant_table_mapping_v1",
              "archive_sha256": archive_hash, "window_sha256": sha256(window_bytes),
              "patent_table_extraction_sha256": sha256(patent_bytes),
              "pubchem_receipt_hashes": receipt_hashes,
              "assay_id": "CHEMBL5734042", "source_activity_count": len(assay_rows),
              "source_molecule_count": len(by_molecule), "status_counts": dict(sorted(summary.items())),
              "rows": mapped, "campaign_ready": False,
              "limitations": ["PubChem synonyms support example identity but do not define the AA assay method.",
                              "A numeric match does not independently prove the patent measurement protocol.",
                              "Censored values retain the ChEMBL and patent relation signs."]}
    data = (json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists():
        if args.output.read_bytes() != data:
            raise FileExistsError("Existing full mapping differs; do not overwrite")
    else:
        with args.output.open("xb") as handle:
            handle.write(data)
    print(json.dumps({"status_counts": report["status_counts"],
                      "report_sha256": sha256(data), "output": str(args.output)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
