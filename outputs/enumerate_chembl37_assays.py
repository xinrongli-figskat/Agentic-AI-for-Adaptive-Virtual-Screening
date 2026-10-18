"""Enumerate ChEMBL_37 single-assay IC50 candidates without using an LLM.

The output is a source-molecule prescreen. It is never a frozen benchmark.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation
import hashlib
import json
import os
from pathlib import Path
import sqlite3
from urllib.parse import quote


ROW_SQL = """
SELECT act.activity_id, act.molregno, md.chembl_id AS molecule_chembl_id,
       cs.canonical_smiles, act.standard_relation, act.standard_value,
       act.standard_units, act.potential_duplicate, act.data_validity_comment,
       act.activity_comment
FROM activities act
LEFT JOIN molecule_dictionary md ON md.molregno = act.molregno
LEFT JOIN compound_structures cs ON cs.molregno = act.molregno
WHERE act.assay_id = ? AND act.standard_type = 'IC50'
ORDER BY act.activity_id
"""
REQUIRED = {
    "activities": {"activity_id", "assay_id", "molregno", "standard_type", "standard_relation",
                   "standard_value", "standard_units", "potential_duplicate", "data_validity_comment"},
    "assays": {"assay_id", "chembl_id", "assay_type", "confidence_score", "tid", "doc_id", "src_id"},
    "target_dictionary": {"tid", "chembl_id", "target_type"},
    "docs": {"doc_id", "chembl_id", "doc_type", "src_id"},
    "molecule_dictionary": {"molregno", "chembl_id"},
    "compound_structures": {"molregno", "canonical_smiles"},
}
THRESHOLD = Decimal(1000)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(16 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def record_signal(row: sqlite3.Row) -> tuple[str, str]:
    """Apply existing source-level support logic; never impute a nonhit."""
    if row["molregno"] is None or not row["molecule_chembl_id"] or not row["canonical_smiles"]:
        return "unknown", "missing_id_or_structure_string"
    if row["data_validity_comment"] not in (None, "", "Manually validated"):
        return "unknown", "validity_flag_needs_review"
    if row["potential_duplicate"] in (True, 1, "1"):
        return "unknown", "source_potential_duplicate"
    factor = {"nM": Decimal(1), "uM": Decimal(1000), "µM": Decimal(1000), "μM": Decimal(1000)}.get(row["standard_units"])
    if factor is None:
        return "unknown", "unsupported_unit"
    try:
        value = Decimal(str(row["standard_value"])) * factor
        if not value.is_finite() or value <= 0:
            return "unknown", "nonpositive_or_nonfinite_potency"
    except (InvalidOperation, TypeError, ValueError):
        return "unknown", "missing_or_nonnumeric_value"
    relation = row["standard_relation"]
    if relation == "=":
        return ("hit_support" if value <= THRESHOLD else "nonhit_support"), "exact_report"
    if relation in ("<", "<=") and value <= THRESHOLD:
        return "hit_support", "upper_bound_below_threshold"
    if (relation == ">" and value >= THRESHOLD) or (relation == ">=" and value > THRESHOLD):
        return "nonhit_support", "lower_bound_above_threshold"
    return "unknown", "bound_crosses_threshold_or_relation_missing"


def source_tier(meta: sqlite3.Row) -> str:
    if meta["assay_src_id"] == 37 and (meta["doc_type"] or "").upper() == "PATENT":
        return "patent_via_bindingdb"
    if meta["assay_src_id"] == 38 and (meta["doc_type"] or "").upper() == "PATENT":
        return "direct_patent"
    if (meta["doc_type"] or "").upper() == "PUBLICATION" and (meta["doi"] or meta["pubmed_id"]):
        return "research_article"
    return "other_or_unknown"


def required_schema(connection: sqlite3.Connection) -> None:
    for table, columns in REQUIRED.items():
        found = {row[1].lower() for row in connection.execute(f"PRAGMA table_info({table})")}
        missing = columns - found
        if missing:
            raise ValueError(f"ChEMBL schema missing {table}: {sorted(missing)}")


def summarize_assay(connection: sqlite3.Connection, meta: sqlite3.Row) -> dict:
    groups: dict[int, set[str]] = defaultdict(set)
    reasons = Counter()
    record_signals = Counter()
    rows_seen = 0
    missing_molregno_rows = 0
    inactive_annotated_hit_rows = 0
    for row in connection.execute(ROW_SQL, (meta["assay_id"],)):
        rows_seen += 1
        signal, reason = record_signal(row)
        record_signals[signal] += 1
        reasons[reason] += 1
        if row["molregno"] is None:
            missing_molregno_rows += 1
        else:
            groups[row["molregno"]].add(signal)
        if signal == "hit_support" and row["activity_comment"] and any(
                word in row["activity_comment"].lower() for word in ("inactive", "inconclusive", "not active")):
            inactive_annotated_hit_rows += 1
    if rows_seen != meta["raw_ic50_records"]:
        raise ValueError(f"Raw count mismatch for {meta['assay_chembl_id']}: {rows_seen} != {meta['raw_ic50_records']}")
    states = Counter()
    for signals in groups.values():
        support = signals - {"unknown"}
        if support == {"hit_support", "nonhit_support"}:
            states["conflict"] += 1
        elif support:
            states[next(iter(support))] += 1
        else:
            states["unknown_only"] += 1
    hits, nonhits = states["hit_support"], states["nonhit_support"]
    usable = hits + nonhits
    return {
        "assay_id": meta["assay_chembl_id"], "target_id": meta["target_chembl_id"],
        "target_name": meta["target_name"], "target_organism": meta["target_organism"],
        "assay_description": meta["description"], "relationship_type": meta["relationship_type"],
        "confidence_score": meta["confidence_score"], "source_tier": source_tier(meta),
        "assay_src_id": meta["assay_src_id"], "doc_type": meta["doc_type"],
        "document_id": meta["document_chembl_id"], "document_title": meta["document_title"],
        "doi": meta["doi"], "pubmed_id": meta["pubmed_id"], "patent_id": meta["patent_id"],
        "raw_ic50_records": rows_seen, "distinct_molregno": len(groups),
        "hit_support_ids": hits, "nonhit_support_ids": nonhits,
        "supported_ids": usable, "conflict_ids": states["conflict"],
        "unknown_only_ids": states["unknown_only"], "missing_molregno_rows": missing_molregno_rows,
        "record_signal_counts": dict(record_signals), "record_reason_counts": dict(reasons),
        "inactive_annotation_hit_rows": inactive_annotated_hit_rows,
        "numeric_prescreen_pass": usable >= 250 and hits >= 30 and nonhits >= 100,
        "preferred_count_prescreen_pass": usable >= 500 and hits >= 30 and nonhits >= 100,
        "campaign_ready": False,
    }


def run(database: Path, sql_path: Path) -> dict:
    sql = sql_path.read_text(encoding="utf-8")
    if sql.count(";") != 1:
        raise ValueError("Expected exactly one read-only candidate SQL statement")
    uri = "file:" + quote(str(database.resolve()), safe="/") + "?mode=ro"
    connection = sqlite3.connect(uri, uri=True)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("PRAGMA query_only=ON")
        connection.execute("PRAGMA temp_store=FILE")
        required_schema(connection)
        raw = connection.execute(sql).fetchall()
        funnel = Counter({"raw_assays_ge_250": len(raw)})
        eligible_meta = []
        for row in raw:
            if row["assay_type"] != "B":
                continue
            funnel["assay_type_B"] += 1
            if row["confidence_score"] is None or row["confidence_score"] < 9:
                continue
            funnel["confidence_ge_9"] += 1
            if row["target_type"] != "SINGLE PROTEIN":
                continue
            funnel["single_protein"] += 1
            eligible_meta.append(row)
        rows = []
        for position, meta in enumerate(eligible_meta, 1):
            result = summarize_assay(connection, meta)
            rows.append(result)
            if result["numeric_prescreen_pass"]:
                funnel["numeric_prescreen_pass"] += 1
                if result["preferred_count_prescreen_pass"]:
                    funnel["preferred_count_prescreen_pass"] += 1
            if position % 100 == 0:
                print(json.dumps({"processed_assays": position, "of": len(eligible_meta),
                                  "numeric_pass_so_far": funnel["numeric_prescreen_pass"]}), flush=True)
        tiers = {}
        for tier in ("research_article", "patent_via_bindingdb", "direct_patent", "other_or_unknown"):
            subset = [row for row in rows if row["source_tier"] == tier]
            subset.sort(key=lambda r: (-min(r["hit_support_ids"], r["nonhit_support_ids"]),
                                       -r["supported_ids"], r["assay_id"]))
            tiers[tier] = {"assays_after_metadata": len(subset),
                           "numeric_prescreen_pass": sum(r["numeric_prescreen_pass"] for r in subset),
                           "top_numeric_candidates": [r["assay_id"] for r in subset if r["numeric_prescreen_pass"]][:30]}
        return {"funnel": dict(funnel), "source_tiers": tiers, "assays": rows,
                "interpretation": "Source-molecule numeric prescreen only; no RDKit standardization or scientific source approval.",
                "campaign_ready": False}
    finally:
        connection.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--sql", type=Path, required=True)
    parser.add_argument("--verified-download", type=Path, required=False)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    if not args.database.is_file() or args.database.stat().st_size < 1_000_000:
        raise ValueError("Database is absent or implausibly small")
    if args.verified_download:
        receipt = json.loads(args.verified_download.read_bytes())
        if receipt.get("status") != "verified" or receipt.get("archive_sha256") != "33c203740555f96067710cdfc1c3c55d890660e5908ec5cbf5817492c290d281":
            raise ValueError("ChEMBL archive is not verified against official checksum")
    scratch = args.output_root / ".sqlite_tmp"
    scratch.mkdir(parents=True, exist_ok=True)
    os.environ["SQLITE_TMPDIR"] = str(scratch.resolve())
    os.environ["TMPDIR"] = str(scratch.resolve())
    database_hash = sha256_file(args.database)
    sql_hash = sha256_file(args.sql)
    code_hash = sha256_file(Path(__file__))
    result = run(args.database, args.sql)
    run_id = hashlib.sha256((database_hash + sql_hash + code_hash).encode()).hexdigest()[:16]
    folder = args.output_root / ("chembl37_assay_prescreen_" + run_id)
    if folder.exists():
        raise FileExistsError(f"Refusing to overwrite previous prescreen: {folder}")
    folder.mkdir(parents=True)
    manifest = {"schema": "chembl37_assay_prescreen_v1", "database_sha256": database_hash,
                "database_bytes": args.database.stat().st_size, "sql_sha256": sql_hash,
                "script_sha256": code_hash, "criteria": {"endpoint": "IC50", "threshold_nM": "1000",
                "assay_type": "B", "minimum_confidence": 9, "target_type": "SINGLE PROTEIN",
                "minimum_source_molecules": 250, "minimum_hits": 30, "minimum_nonhits": 100},
                "numeric_results_are_frozen_labels": False, "campaign_ready": False}
    for name, value in (("manifest.json", manifest), ("result.json", result)):
        (folder / name).write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output_dir": str(folder), "funnel": result["funnel"],
                      "source_tiers": result["source_tiers"], "campaign_ready": False}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
