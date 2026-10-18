"""Reconcile every ChEMBL TNAP AID 1056 IC50 with primary PubChem data."""
from __future__ import annotations

import argparse
from collections import Counter
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import sqlite3
from urllib.parse import quote

from enumerate_chembl37_assays import sha256_file


QUERY = """
SELECT act.activity_id, act.standard_relation, act.standard_value,
       act.standard_units, act.potential_duplicate, act.data_validity_comment,
       records.src_compound_id AS sid, mol.chembl_id AS molecule_chembl_id
FROM activities act
JOIN assays a ON a.assay_id=act.assay_id
LEFT JOIN compound_records records ON records.record_id=act.record_id
LEFT JOIN molecule_dictionary mol ON mol.molregno=act.molregno
WHERE a.chembl_id='CHEMBL1738510' AND act.standard_type='IC50'
ORDER BY act.activity_id
"""


def verify(path: Path, expected: str) -> None:
    if sha256_file(path) != expected:
        raise ValueError(f"Source changed: {path}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--pubchem-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    selection = json.loads(args.selection.read_text())
    if selection["assay_id"] != "CHEMBL1738510" or selection["database_sha256"] != sha256_file(args.database):
        raise ValueError("Selection and database mismatch")
    receipt = json.loads((args.pubchem_dir / "receipt.json").read_text())
    full_receipt = json.loads((args.pubchem_dir / "full_receipt.json").read_text())
    if receipt["aid"] != 1056 or full_receipt["aid"] != 1056:
        raise ValueError("Unexpected PubChem AID")
    for item in receipt["receipts"]:
        verify(args.pubchem_dir / item["filename"], item["sha256"])
    verify(args.pubchem_dir / "full.json", full_receipt["sha256"])
    source = json.loads((args.pubchem_dir / "full.json").read_text())["PC_AssaySubmit"]
    description = source["assay"]["descr"]
    result_names = {item["tid"]: item["name"] for item in description["results"]}
    if result_names.get(1) != "IC50_Mean_Qualifier" or result_names.get(2) != "IC50_Mean":
        raise ValueError("Unexpected PubChem readout columns")
    by_sid = {str(item["sid"]): item for item in source["data"]}
    if len(by_sid) != len(source["data"]):
        raise ValueError("Repeated PubChem SID")
    uri = "file:" + quote(str(args.database.resolve()), safe="/") + "?mode=ro"
    with sqlite3.connect(uri, uri=True) as connection:
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA query_only=ON")
        records = [dict(row) for row in connection.execute(QUERY)]
    if len(records) != selection["ic50_records_examined"]:
        raise ValueError("ChEMBL record count differs from fixed sample selection")
    sample_ids = {row["activity_id"] for rows in selection["main_sample"].values() for row in rows}
    aligned, counts = [], Counter()
    for record in records:
        sid = str(record["sid"])
        source_row = by_sid.get(sid)
        readouts = {item["tid"]: item["value"] for item in source_row["data"]} if source_row else {}
        relation = readouts.get(1, {}).get("sval")
        value_uM = readouts.get(2, {}).get("fval")
        if source_row is None:
            status = "sid_missing"
        elif relation is None or value_uM is None:
            status = "source_ic50_mean_missing"
        elif record["standard_units"] != "nM":
            status = "unexpected_chEMBL_unit"
        elif record["standard_relation"] != relation:
            status = "relation_mismatch"
        elif record["standard_value"] is None:
            status = "chEMBL_value_missing"
        elif abs(Decimal(str(record["standard_value"])) - Decimal(str(value_uM)) * 1000) > Decimal("0.001"):
            status = "value_mismatch_gt_0.001_nM"
        else:
            status = "matched"
        counts[status] += 1
        aligned.append({**record, "pubchem_aid": 1056,
                        "pubchem_ic50_mean_qualifier": relation,
                        "pubchem_ic50_mean_uM": value_uM,
                        "pubchem_activity_outcome_code": source_row.get("outcome") if source_row else None,
                        "alignment_status": status,
                        "fixed_main_sample": record["activity_id"] in sample_ids})
    if len([row for row in aligned if row["fixed_main_sample"]]) != 12:
        raise ValueError("Fixed main sample is incomplete in reconciled source")
    target = description.get("target") or []
    summary = {"schema": "chembl37_pubchem_tnap_alignment_v1", "assay_id": "CHEMBL1738510",
               "pubchem_aid": 1056, "chEMBL_records": len(records), "pubchem_substance_rows": len(by_sid),
               "alignment_counts": dict(counts), "fixed_main_sample_matched": sum(
                   row["fixed_main_sample"] and row["alignment_status"] == "matched" for row in aligned),
               "source_target": target, "source_readout_columns": {"qualifier_tid": 1, "ic50_mean_tid": 2},
               "source_method": "Cell-free TNAP enzyme activity using CDP-star substrate and luminescence, fitted dose-response IC50_Mean",
               "source_protein_preparation_note": "AID names human TNAP accession and says protein was supplied by Jose Luis Millan; exact expression construct/preparation is not specified in the AID protocol.",
               "source_activity_threshold_note": "PubChem Active/Inactive uses its own threshold near 100 uM; the proposed benchmark uses 1 uM on measured IC50. They are not equivalent labels.",
               "source_endpoint_resolved": False, "scientific_review_complete": False,
               "campaign_ready": False, "database_sha256": selection["database_sha256"],
               "selection_sha256": sha256_file(args.selection), "pubchem_full_sha256": full_receipt["sha256"]}
    args.output_dir.mkdir(parents=True, exist_ok=False)
    for name, data in (("record_alignment.json", aligned), ("summary.json", summary)):
        (args.output_dir / name).write_text(json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
    hashes = {name: sha256_file(args.output_dir / name) for name in ("record_alignment.json", "summary.json")}
    (args.output_dir / "file_hashes.json").write_text(json.dumps(hashes, sort_keys=True, indent=2) + "\n")
    print(json.dumps({"output_dir": str(args.output_dir), "alignment_counts": dict(counts),
                      "fixed_main_sample_matched": summary["fixed_main_sample_matched"],
                      "source_endpoint_resolved": False, "campaign_ready": False}))


if __name__ == "__main__":
    main()
