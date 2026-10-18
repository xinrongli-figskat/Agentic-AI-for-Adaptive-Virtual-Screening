"""Freeze 6+6 source-record checks before looking up an assay's primary source."""
from __future__ import annotations

import argparse
from collections import defaultdict
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import sqlite3
from urllib.parse import quote

from enumerate_chembl37_assays import record_signal, sha256_file


SQL = """
SELECT act.activity_id, act.molregno, mol.chembl_id AS molecule_chembl_id,
       structures.canonical_smiles, act.standard_relation, act.standard_value,
       act.standard_units, act.potential_duplicate, act.data_validity_comment,
       act.activity_comment, act.type, act.relation, act.value, act.units,
       records.record_id, records.src_compound_id, records.compound_key,
       records.compound_name, docs.chembl_id AS document_chembl_id
FROM activities act
LEFT JOIN molecule_dictionary mol ON mol.molregno=act.molregno
LEFT JOIN compound_structures structures ON structures.molregno=act.molregno
LEFT JOIN compound_records records ON records.record_id=act.record_id
LEFT JOIN docs ON docs.doc_id=act.doc_id
JOIN assays assays ON assays.assay_id=act.assay_id
WHERE assays.chembl_id=? AND act.standard_type='IC50'
ORDER BY act.activity_id
"""


def order_key(row: dict) -> str:
    return hashlib.sha256(("task1-v5-source-audit|" + str(row["activity_id"])).encode()).hexdigest()


def select(rows: list[dict], per_class: int = 6) -> dict:
    groups = defaultdict(list)
    for row in rows:
        row = {**row, "signal": record_signal(row)[0], "selection_hash": order_key(row)}
        if row["molecule_chembl_id"]:
            groups[row["molecule_chembl_id"]].append(row)
    excluded_conflicts = []
    classes = {"hit_support": [], "nonhit_support": []}
    for molecule, entries in groups.items():
        signals = {r["signal"] for r in entries} - {"unknown"}
        if len(signals) == 2:
            excluded_conflicts.append({"molecule_chembl_id": molecule,
                                       "activity_ids": sorted(r["activity_id"] for r in entries)})
            continue
        if len(signals) == 1:
            signal = next(iter(signals))
            classes[signal].extend(r for r in entries if r["signal"] == signal)
    chosen = {}
    for signal, eligible in classes.items():
        seen = set()
        chosen[signal] = []
        for row in sorted(eligible, key=lambda r: (r["selection_hash"], r["activity_id"])):
            if row["molecule_chembl_id"] in seen:
                continue
            seen.add(row["molecule_chembl_id"])
            chosen[signal].append(row)
            if len(chosen[signal]) == per_class:
                break
    # Two exact, eligible measurements closest to the fixed threshold are
    # supplementary edge checks; they never replace the 6+6 main sample.
    near = []
    for row in rows:
        if row["standard_relation"] != "=" or row["standard_units"] != "nM":
            continue
        try:
            distance = abs(Decimal(str(row["standard_value"])) - Decimal(1000))
        except Exception:
            continue
        near.append((distance, order_key(row), row))
    near.sort(key=lambda x: (x[0], x[1]))
    return {"main_sample": chosen, "edge_sample": [item[2] for item in near[:2]],
            "conflicting_source_ids": excluded_conflicts,
            "main_sample_complete": all(len(chosen[k]) == per_class for k in chosen),
            "sample_rule": "SHA256(task1-v5-source-audit|activity_id), first distinct source molecule IDs in each class"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--assay-id", required=True)
    parser.add_argument("--source-rules", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    if not args.assay_id.startswith("CHEMBL") or not args.assay_id[6:].isdigit():
        raise ValueError("Invalid ChEMBL assay ID")
    db_hash = sha256_file(args.database)
    rules_hash = sha256_file(args.source_rules)
    code_hash = sha256_file(Path(__file__))
    uri = "file:" + quote(str(args.database.resolve()), safe="/") + "?mode=ro"
    with sqlite3.connect(uri, uri=True) as connection:
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA query_only=ON")
        rows = [dict(row) for row in connection.execute(SQL, (args.assay_id,))]
    if not rows:
        raise ValueError("Assay has no IC50 records in verified SQLite release")
    result = select(rows)
    run_id = hashlib.sha256((db_hash + rules_hash + code_hash + args.assay_id).encode()).hexdigest()[:16]
    folder = args.output_root / ("source_sample_" + args.assay_id + "_" + run_id)
    folder.mkdir(parents=True, exist_ok=False)
    result.update({"assay_id": args.assay_id, "database_sha256": db_hash,
                   "source_rules_sha256": rules_hash, "script_sha256": code_hash,
                   "ic50_records_examined": len(rows), "source_lookup_performed": False,
                   "source_endpoint_resolved": False, "campaign_ready": False})
    path = folder / "selection.json"
    path.write_text(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
    print(json.dumps({"folder": str(folder), "sha256": sha256_file(path),
                      "hits_selected": len(result["main_sample"]["hit_support"]),
                      "nonhits_selected": len(result["main_sample"]["nonhit_support"]),
                      "source_endpoint_resolved": False}))


if __name__ == "__main__":
    main()
