"""Freeze a read-only S1PR1 source-audit sample from the verified v4 archive.

This is a post-exposure source review, not a compound-label assignment or a
campaign export. It makes no network calls and never edits the archived run.
"""
from __future__ import annotations

import argparse
import csv
from decimal import Decimal, InvalidOperation
import hashlib
import io
import json
from pathlib import Path
import zipfile

from verify_task1_v4_archive import verify


ASSAY_ID = "CHEMBL5734042"
TARGET_ID = "CHEMBL4333"
WINDOW_PATH = "run/evidence/E0174_thin_target_window.json"
CONFIG_PATH = "run/source_snapshot/vendor/discovery_criteria.json"
METADATA_PATH = "run/evidence/E0176_assay_metadata.json"
RULES_NAME = "task1_v5_source_adjudication_rules_20261016.md"
PLAN_NAME = "task1_v5_execution_plan_20261016.md"


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def signal(row: dict, config: dict) -> tuple[str, str]:
    """Mirror the archived discovery-v0 record_signal rules for this sample."""
    if row.get("standard_type") != config["standard_type"]:
        return "unknown", "different_endpoint"
    if row.get("assay_type") != config["assay_type_for_record_signals"]:
        return "unknown", "outside_initial_assay_scope"
    if not row.get("molecule_chembl_id") or not row.get("canonical_smiles") or not row.get("assay_chembl_id"):
        return "unknown", "missing_id_or_structure_string"
    if row.get("data_validity_comment") not in config["validity_comments_allowed"]:
        return "unknown", "validity_flag_needs_review"
    if config["exclude_flagged_potential_duplicates_from_signals"] and row.get("potential_duplicate") in (True, 1, "1"):
        return "unknown", "source_potential_duplicate"
    factor = {"nM": Decimal(1), "uM": Decimal(1000), "µM": Decimal(1000), "μM": Decimal(1000)}.get(row.get("standard_units"))
    if factor is None:
        return "unknown", "unsupported_unit"
    try:
        value = Decimal(str(row.get("standard_value"))) * factor
        if not value.is_finite() or value <= 0:
            return "unknown", "nonpositive_or_nonfinite_potency"
    except InvalidOperation:
        return "unknown", "missing_or_nonnumeric_value"
    threshold = Decimal(config["hit_threshold_nM"])
    relation = row.get("standard_relation")
    if relation == "=":
        return ("hit_support" if value <= threshold else "nonhit_support"), "exact_report"
    if relation in ("<", "<=") and value <= threshold:
        return "hit_support", "upper_bound_below_threshold"
    if (relation == ">" and value >= threshold) or (relation == ">=" and value > threshold):
        return "nonhit_support", "lower_bound_above_threshold"
    return "unknown", "bound_crosses_threshold_or_relation_missing"


def sample_records(rows: list[dict], config: dict, expected_profile: dict) -> dict:
    if len({str(r["activity_id"]) for r in rows}) != len(rows):
        raise ValueError("Duplicate activity IDs in the archived window")
    classified = []
    by_molecule: dict[str, set[str]] = {}
    by_molecule_rows: dict[str, list[dict]] = {}
    for row in rows:
        if row.get("assay_chembl_id") != ASSAY_ID or row.get("target_chembl_id") != TARGET_ID:
            raise ValueError("Unexpected assay or target in sample input")
        state, reason = signal(row, config)
        item = {"activity_id": str(row["activity_id"]), "molecule_chembl_id": row.get("molecule_chembl_id"),
                "record_signal": state, "record_reason": reason, "raw_record": row}
        classified.append(item)
        molecule = row.get("molecule_chembl_id")
        if molecule:
            by_molecule.setdefault(molecule, set()).add(state)
            by_molecule_rows.setdefault(molecule, []).append(item)
    conflict_ids = sorted(m for m, states in by_molecule.items() if {"hit_support", "nonhit_support"} <= states)
    support_ids = {}
    for category in ("hit_support", "nonhit_support"):
        support_ids[category] = {m for m, states in by_molecule.items() if category in states and m not in conflict_ids}
    counts = {"hit_support_ids": len(support_ids["hit_support"]),
              "nonhit_support_ids": len(support_ids["nonhit_support"]),
              "supported_ids": len(support_ids["hit_support"] | support_ids["nonhit_support"]),
              "threshold_disagreement_ids": len(conflict_ids),
              "unknown_evidence_ids": sum("unknown" in states for states in by_molecule.values())}
    for name, value in counts.items():
        if value != expected_profile[name]:
            raise ValueError(f"Recomputed {name}={value}, archived profile={expected_profile[name]}")
    selected = []
    for category in ("hit_support", "nonhit_support"):
        eligible = [item for item in classified if item["record_signal"] == category
                    and item["molecule_chembl_id"] in support_ids[category]]
        eligible.sort(key=lambda item: (sha256(("task1-v5-source-audit|" + item["activity_id"]).encode()),
                                        item["activity_id"]))
        seen = set()
        for item in eligible:
            molecule = item["molecule_chembl_id"]
            if molecule in seen:
                continue
            seen.add(molecule)
            entry = {key: item[key] for key in ("activity_id", "molecule_chembl_id", "record_signal", "record_reason", "raw_record")}
            entry["sort_sha256"] = sha256(("task1-v5-source-audit|" + item["activity_id"]).encode())
            entry["same_molecule_records"] = sorted(
                by_molecule_rows[molecule], key=lambda other: int(other["activity_id"]))
            selected.append(entry)
            if len(seen) == 6:
                break
    def distance(item: dict) -> tuple[Decimal, str]:
        row = item["raw_record"]
        factor = {"nM": Decimal(1), "uM": Decimal(1000), "µM": Decimal(1000), "μM": Decimal(1000)}.get(row.get("standard_units"))
        try:
            value = Decimal(str(row.get("standard_value"))) * factor if factor is not None else None
        except InvalidOperation:
            value = None
        return ((abs(value - Decimal(config["hit_threshold_nM"])) if value is not None and value.is_finite()
                 else Decimal("Infinity")), item["activity_id"])
    boundaries = sorted(classified, key=distance)[:2]
    return {"counts": counts, "selected": selected,
            "conflict_molecule_ids": conflict_ids,
            "conflict_records": [item for item in classified if item["molecule_chembl_id"] in conflict_ids],
            "boundary_records": [{**item, "distance_nM": str(distance(item)[0])} for item in boundaries],
            "assay_records_in_window": len(rows),
            "distinct_molecule_ids_in_window": len(by_molecule)}


def build(archive: Path, rules_dir: Path, expected_archive_sha256: str) -> tuple[dict, bytes]:
    verified = verify(archive, expected_archive_sha256)
    lock_path = rules_dir / "task1_v5_protocol_lock_20261016.json"
    lock = json.loads(lock_path.read_text(encoding="utf-8-sig"))
    if lock["status"] != "locked_before_further_row_level_source_audit_in_this_workspace":
        raise ValueError("Source rules are not locked")
    for name in (RULES_NAME, PLAN_NAME):
        actual = sha256((rules_dir / name).read_bytes())
        if actual != lock["locked_files"][name]:
            raise ValueError(f"Locked rule file changed: {name}")
    with zipfile.ZipFile(archive) as z:
        state = json.loads(z.read("run/state.json"))
        profile = state["profiles"][TARGET_ID]
        if not profile["retrieval_complete"] or profile["raw_evidence_id"] != "E0174":
            raise ValueError("Target window is incomplete or unexpected")
        if state["assays"][ASSAY_ID].get("decision") is not None:
            raise ValueError("Assay already has a decision in the archived run")
        for eid, member in (("E0174", WINDOW_PATH), ("E0176", METADATA_PATH)):
            entry = state["evidence"][eid]
            if "run/" + entry["path"] != member or sha256(z.read(member)) != entry["sha256"]:
                raise ValueError(f"Archived {eid} evidence mismatch")
        window = json.loads(z.read(WINDOW_PATH))
        if not window["complete"] or window["target_id"] != TARGET_ID:
            raise ValueError("Unexpected raw target window")
        config = json.loads(z.read(CONFIG_PATH))
        metadata = json.loads(z.read(METADATA_PATH))
        if metadata["assay"]["assay_chembl_id"] != ASSAY_ID:
            raise ValueError("Unexpected assay metadata")
        expected = next(x for x in profile["top_assays_in_window"] if x["assay_chembl_id"] == ASSAY_ID)
        rows = [r for r in window["records"] if r.get("assay_chembl_id") == ASSAY_ID]
        sample = sample_records(rows, config, expected)
        selection = {
            "schema": "task1_v5_s1pr1_fixed_source_sample_v1",
            "status": "fixed_post_exposure_sample_source_endpoint_unresolved",
            "archive_sha256": verified["sha256"],
            "protocol_lock_sha256": sha256(lock_path.read_bytes()),
            "rules_sha256": lock["locked_files"][RULES_NAME],
            "source_evidence": {"target_window": {"path": WINDOW_PATH, "sha256": sha256(z.read(WINDOW_PATH))},
                                "assay_metadata": {"path": METADATA_PATH, "sha256": sha256(z.read(METADATA_PATH))},
                                "discovery_criteria": {"path": CONFIG_PATH, "sha256": sha256(z.read(CONFIG_PATH))}},
            "assay_id": ASSAY_ID, "target_id": TARGET_ID,
            "metadata": metadata, "sample": sample,
            "limitations": ["Preliminary source-ID signals, not curated compound labels.",
                            "No patent example, source row, or endpoint has yet been aligned.",
                            "No campaign labels are exported or revealed by this selection."]}
    return selection, canonical_bytes(selection)


def csv_bytes(selection: dict) -> bytes:
    columns = ["sample_role", "preview_support", "activity_id", "molecule_chembl_id",
               "standard_relation", "standard_value", "standard_units", "document_chembl_id",
               "patent_example", "patent_table", "patent_column", "patent_page",
               "patent_relation", "patent_value", "patent_units", "source_record_id",
               "method_source", "receptor", "construct_or_cell", "match_status", "evidence_url", "notes"]
    out = io.StringIO(newline="")
    writer = csv.DictWriter(out, fieldnames=columns)
    writer.writeheader()
    entries = [("main", item) for item in selection["sample"]["selected"]]
    entries += [("boundary", item) for item in selection["sample"]["boundary_records"]]
    entries += [("conflict", item) for item in selection["sample"]["conflict_records"]]
    for role, item in entries:
        raw = item["raw_record"]
        writer.writerow({"sample_role": role, "preview_support": item["record_signal"],
                         "activity_id": item["activity_id"], "molecule_chembl_id": item["molecule_chembl_id"],
                         "standard_relation": raw.get("standard_relation"), "standard_value": raw.get("standard_value"),
                         "standard_units": raw.get("standard_units"), "document_chembl_id": raw.get("document_chembl_id")})
    return out.getvalue().encode("utf-8-sig")


def write_immutable(path: Path, data: bytes) -> None:
    if path.exists():
        if path.read_bytes() != data:
            raise FileExistsError(f"Existing frozen output differs: {path}")
        return
    with path.open("xb") as handle:
        handle.write(data)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--expected-sha256", required=True)
    parser.add_argument("--rules-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    selection, payload = build(args.archive, args.rules_dir, args.expected_sha256)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    table = csv_bytes(selection)
    write_immutable(args.output_dir / "fixed_selection.json", payload)
    write_immutable(args.output_dir / "source_alignment_template.csv", table)
    print(json.dumps({"status": selection["status"], "assay_id": ASSAY_ID,
                      "source_ids": selection["sample"]["counts"],
                      "records_in_assay_window": selection["sample"]["assay_records_in_window"],
                      "main_sample": {category: sum(item["record_signal"] == category for item in selection["sample"]["selected"])
                                      for category in ("hit_support", "nonhit_support")},
                      "boundary_record_count": len(selection["sample"]["boundary_records"]),
                      "conflict_molecule_count": len(selection["sample"]["conflict_molecule_ids"]),
                      "selection_sha256": sha256(payload), "template_sha256": sha256(table),
                      "output_dir": str(args.output_dir)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
